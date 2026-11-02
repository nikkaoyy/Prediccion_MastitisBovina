import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:mastitis_app/data/app_database.dart';
import 'package:mastitis_app/data/repository.dart';
import 'package:mastitis_app/models/lite_model.dart';
import 'package:mastitis_app/sync/model_store.dart';
import 'package:mastitis_app/sync/sync_api.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

String readModelsFile(String name) => File('../models/$name').readAsStringSync();

LiteModel loadModel() => LiteModel.fromJsonString(readModelsFile('model_lite.json'));

void initFfi() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
}

Future<(Database, Repository, ModelStore)> openTestRepo({DateTime Function()? clock}) async {
  initFfi();
  final db = await AppDatabase.open(path: inMemoryDatabasePath);
  final repo = Repository(db, clock: clock);
  final store = ModelStore(repo, assetLoader: () async => readModelsFile('model_lite.json'));
  await store.load();
  return (db, repo, store);
}

/// Servidor simulado con la misma semántica que server/app/routers/sync.py:
/// idempotente, aceptación parcial, 'retry' por dependencias y cursores por seq.
class FakeServer implements SyncApi {
  FakeServer({required this.manifestJson, required this.liteBytes});

  bool online = true;
  bool authorized = true;
  int pushCalls = 0;
  Map<String, dynamic> manifestJson;
  Uint8List liteBytes;

  final vacas = <String, Map<String, dynamic>>{};
  final mediciones = <String, Map<String, dynamic>>{};
  final confirmaciones = <String, Map<String, dynamic>>{};
  final _order = <String, List<String>>{'vacas': [], 'mediciones': [], 'confirmaciones': []};
  final acceptedCount = <String, int>{};

  void _guard() {
    if (!online) throw NetworkException('Sin conexión (simulada)');
    if (!authorized) throw ApiException('Token inválido', status: 401);
  }

  Map<String, dynamic> _item(String id, String status, [String? reason]) =>
      {'id': id, 'status': status, 'reason': ?reason};

  @override
  Future<Map<String, dynamic>> push(Map<String, Object?> payload) async {
    _guard();
    pushCalls++;
    final out = <String, List<Map<String, dynamic>>>{
      'vacas': [], 'mediciones': [], 'confirmaciones': []
    };

    for (final raw in (payload['vacas'] as List)) {
      final v = Map<String, dynamic>.from(raw as Map);
      final id = v['id'] as String;
      if (vacas.containsKey(id)) {
        out['vacas']!.add(vacas[id]!['arete'] == v['arete'] && vacas[id]!['nombre'] == v['nombre']
            ? _item(id, 'duplicate')
            : _item(id, 'rejected', 'conflicto'));
      } else if (vacas.values.any((x) => x['arete'] == v['arete'])) {
        out['vacas']!.add(_item(id, 'rejected', 'arete duplicado en la finca'));
      } else {
        vacas[id] = v;
        _order['vacas']!.add(id);
        acceptedCount[id] = (acceptedCount[id] ?? 0) + 1;
        out['vacas']!.add(_item(id, 'accepted'));
      }
    }
    for (final raw in (payload['mediciones'] as List)) {
      final m = Map<String, dynamic>.from(raw as Map);
      final id = m['id'] as String;
      final ph = (m['ph_leche'] as num).toDouble();
      if (ph < 5.5 || ph > 8.0) {
        out['mediciones']!.add(_item(id, 'rejected', 'ph_leche: fuera de rango'));
      } else if (mediciones.containsKey(id)) {
        out['mediciones']!.add(_item(id, 'duplicate'));
      } else if (!vacas.containsKey(m['vaca_id'])) {
        out['mediciones']!.add(_item(id, 'retry', 'vaca desconocida en el servidor'));
      } else {
        mediciones[id] = m;
        _order['mediciones']!.add(id);
        acceptedCount[id] = (acceptedCount[id] ?? 0) + 1;
        out['mediciones']!.add(_item(id, 'accepted'));
      }
    }
    for (final raw in (payload['confirmaciones'] as List)) {
      final c = Map<String, dynamic>.from(raw as Map);
      final id = c['id'] as String;
      if (confirmaciones.containsKey(id)) {
        out['confirmaciones']!.add(_item(id, 'duplicate'));
      } else if (!mediciones.containsKey(c['medicion_id'])) {
        out['confirmaciones']!.add(_item(id, 'retry', 'medición desconocida en el servidor'));
      } else {
        confirmaciones[id] = c;
        _order['confirmaciones']!.add(id);
        acceptedCount[id] = (acceptedCount[id] ?? 0) + 1;
        out['confirmaciones']!.add(_item(id, 'accepted'));
      }
    }
    return {'results': out, 'model_version': manifestJson['model_version']};
  }

  /// Registros creados por "otro teléfono" de la misma finca.
  void seedFromOtherDevice(Map<String, dynamic> vaca, [List<Map<String, dynamic>> meds = const []]) {
    vacas[vaca['id'] as String] = vaca;
    _order['vacas']!.add(vaca['id'] as String);
    for (final m in meds) {
      mediciones[m['id'] as String] = m;
      _order['mediciones']!.add(m['id'] as String);
    }
  }

  @override
  Future<Map<String, dynamic>> pull({
    required int cursorVacas,
    required int cursorMediciones,
    required int cursorConfirmaciones,
    int limit = 500,
  }) async {
    _guard();
    List<dynamic> page(String kind, Map<String, Map<String, dynamic>> store, int cursor, void Function(int) setCursor, void Function() more) {
      final ids = _order[kind]!;
      final slice = ids.skip(cursor).take(limit + 1).toList();
      if (slice.length > limit) more();
      final taken = slice.take(limit).toList();
      setCursor(cursor + taken.length);
      return taken.map((id) => store[id]!).toList();
    }

    var hasMore = false;
    var cv = cursorVacas, cm = cursorMediciones, cc = cursorConfirmaciones;
    final v = page('vacas', vacas, cursorVacas, (c) => cv = c, () => hasMore = true);
    final m = page('mediciones', mediciones, cursorMediciones, (c) => cm = c, () => hasMore = true);
    final c = page('confirmaciones', confirmaciones, cursorConfirmaciones, (x) => cc = x, () => hasMore = true);
    return {
      'vacas': v,
      'mediciones': m,
      'confirmaciones': c,
      'cursors': {'vacas': cv, 'mediciones': cm, 'confirmaciones': cc},
      'has_more': hasMore,
    };
  }

  @override
  Future<Map<String, dynamic>> manifest() async {
    _guard();
    return manifestJson;
  }

  @override
  Future<Uint8List> downloadLite() async {
    _guard();
    return liteBytes;
  }

  @override
  void close() {}
}

FakeServer fakeServerWithCurrentModel() {
  final json = readModelsFile('model_lite.json');
  final bytes = Uint8List.fromList(utf8.encode(json));
  return FakeServer(
    manifestJson: {
      'model_version': LiteModel.fromJsonString(json).version,
      'files': {'model_lite.json': sha256.convert(bytes).toString()},
    },
    liteBytes: bytes,
  );
}

String sha256Hex(Uint8List bytes) => sha256.convert(bytes).toString();

/// Envuelve un servidor y simula un corte de red tras N envíos exitosos.
class FlakyApi implements SyncApi {
  FlakyApi(this.inner, {required this.failAfterPushes});
  final FakeServer inner;
  final int failAfterPushes;
  int _pushes = 0;

  @override
  Future<Map<String, dynamic>> push(Map<String, Object?> payload) async {
    if (_pushes >= failAfterPushes) throw NetworkException('Se cortó la conexión (simulada)');
    _pushes++;
    return inner.push(payload);
  }

  @override
  Future<Map<String, dynamic>> pull({
    required int cursorVacas,
    required int cursorMediciones,
    required int cursorConfirmaciones,
    int limit = 500,
  }) => inner.pull(
      cursorVacas: cursorVacas,
      cursorMediciones: cursorMediciones,
      cursorConfirmaciones: cursorConfirmaciones,
      limit: limit);

  @override
  Future<Map<String, dynamic>> manifest() => inner.manifest();

  @override
  Future<Uint8List> downloadLite() => inner.downloadLite();

  @override
  void close() {}
}
