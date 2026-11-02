import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:mastitis_app/data/repository.dart';
import 'package:mastitis_app/models/entities.dart';
import 'package:mastitis_app/sync/model_store.dart';
import 'package:mastitis_app/sync/sync_service.dart';

import 'helpers.dart';

MedicionInput input({double ph = 6.9}) => MedicionInput(
      edad: 5, raza: 'Holstein', numeroDePartos: 3, etapaDeLactancia: 1,
      antecedentesDeMastitis: 0, phLeche: ph,
    );

void main() {
  late Repository repo;
  late ModelStore store;
  late FakeServer server;
  late SyncService service;

  setUp(() async {
    final opened = await openTestRepo();
    repo = opened.$2;
    store = opened.$3;
    server = fakeServerWithCurrentModel();
    service = SyncService(repo: repo, modelStore: store, apiFactory: () async => server, batchSize: 3);
  });

  Future<void> registerData(int cows, {int measurementsPerCow = 1}) async {
    for (var i = 0; i < cows; i++) {
      final v = await repo.crearVaca(arete: 'A-$i');
      for (var j = 0; j < measurementsPerCow; j++) {
        final m = await repo.registrarMedicion(
            vacaId: v.id, input: input(ph: 6.5 + j / 10), model: store.current);
        if (j == 0) await repo.registrarConfirmacion(medicionId: m.id, grado: CmtGrade.dos);
      }
    }
  }

  test('sin conexión: nada se pierde y todo queda pendiente', () async {
    await registerData(2);
    server.online = false;
    final report = await service.syncNow();
    expect(report.ok, isFalse);
    expect(report.error, contains('Sin conexión'));
    expect(await repo.pendingCount(), 6); // 2 vacas + 2 mediciones + 2 confirmaciones
    expect(server.vacas, isEmpty);
  });

  test('offline → online: se envía todo exactamente una vez, en lotes pequeños', () async {
    await registerData(3, measurementsPerCow: 2);
    server.online = false;
    await service.syncNow();

    server.online = true;
    final report = await service.syncNow();
    expect(report.ok, isTrue);
    expect(await repo.pendingCount(), 0);
    expect(server.vacas.length, 3);
    expect(server.mediciones.length, 6);
    expect(server.confirmaciones.length, 3);
    expect(server.acceptedCount.values.every((n) => n == 1), isTrue);
    expect(server.pushCalls, greaterThan(1), reason: 'batchSize=3 obliga a varios envíos');
  });

  test('corte de red a mitad de la sincronización: se reanuda sin duplicar', () async {
    await registerData(4);
    final flaky = FlakyApi(server, failAfterPushes: 1);
    final flakyService = SyncService(
        repo: repo, modelStore: store, apiFactory: () async => flaky, batchSize: 3);

    final first = await flakyService.syncNow();
    expect(first.ok, isFalse);
    final pendingAfterFailure = await repo.pendingCount();
    expect(pendingAfterFailure, greaterThan(0));
    expect(pendingAfterFailure, lessThan(12));

    final second = await service.syncNow();
    expect(second.ok, isTrue);
    expect(await repo.pendingCount(), 0);
    expect(server.acceptedCount.values.every((n) => n == 1), isTrue);
    expect(server.vacas.length + server.mediciones.length + server.confirmaciones.length, 12);
  });

  test('reenviar un lote ya aceptado se reconoce como duplicado', () async {
    await registerData(1);
    await service.syncNow();
    // Simula que la respuesta se perdió: el cliente vuelve a marcar pendiente.
    await repo.db.update('vacas', {'sync_state': 'pending'});
    await repo.db.update('mediciones', {'sync_state': 'pending'});
    final report = await service.syncNow();
    expect(report.duplicates, 2);
    expect(report.accepted, 0);
    expect(await repo.pendingCount(), 0);
    expect(server.vacas.length, 1);
  });

  test('registros inválidos para el servidor se marcan rechazados y no se reintentan', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    // Se fuerza un pH que el servidor rechaza (la app lo impediría en el formulario).
    await repo.db.insert('mediciones', {
      ...(await repo.registrarMedicion(vacaId: v.id, input: input(), model: store.current)).toRow(),
      'id': 'bad-1',
      'ph_leche': 9.9,
    });
    final report = await service.syncNow();
    expect(report.rejected, 1);
    expect(await repo.rejectedCount(), 1);
    expect(await repo.pendingCount(), 0);
    final again = await service.syncNow();
    expect(again.rejected, 0);
  });

  test('si solo hay "retry" la sincronización termina sin ciclar', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    await repo.registrarMedicion(vacaId: v.id, input: input(), model: store.current);
    // La vaca ya "existe" como synced localmente pero el servidor la desconoce.
    await repo.db.update('vacas', {'sync_state': 'synced'});
    final report = await service.syncNow();
    expect(report.retried, 1);
    expect(await repo.pendingCount(), 1);
  });

  test('pull trae datos de otros dispositivos con paginación y sin duplicar', () async {
    for (var i = 0; i < 5; i++) {
      server.seedFromOtherDevice({'id': 'srv-$i', 'arete': 'S-$i', 'nombre': null});
    }
    final first = await service.syncNow();
    expect(first.pulled, 5);
    expect((await repo.vacas()).length, 5);
    final second = await service.syncNow();
    expect(second.pulled, 0);
    expect(await repo.getMeta('cursor_vacas'), '5');
  });

  test('error de autenticación se informa y no borra datos', () async {
    await registerData(1);
    server.authorized = false;
    final report = await service.syncNow();
    expect(report.unauthorized, isTrue);
    expect(await repo.pendingCount(), 3);
  });

  test('sin servidor configurado no intenta sincronizar', () async {
    final unconfigured = SyncService(repo: repo, modelStore: store, apiFactory: () async => null);
    final report = await unconfigured.syncNow();
    expect(report.error, 'Servidor no configurado');
  });

  test('mismo arete creado en dos teléfonos: se adopta la vaca del servidor y no se pierde nada', () async {
    // El otro teléfono ya sincronizó la vaca "X-1" con su propio id.
    server.seedFromOtherDevice({'id': 'srv-1', 'arete': 'X-1', 'nombre': 'Lola'});

    final local = await repo.crearVaca(arete: 'X-1');
    final m = await repo.registrarMedicion(vacaId: local.id, input: input(ph: 7.1), model: store.current);
    await repo.registrarConfirmacion(medicionId: m.id, grado: CmtGrade.dos, ciegoAlPh: true);

    final report = await service.syncNow();
    expect(report.ok, isTrue, reason: report.summary);

    // Una sola vaca local, con el id del servidor y su historial reasignado.
    final cows = await repo.vacas();
    expect(cows.length, 1);
    expect(cows.single.vaca.id, 'srv-1');
    expect(await repo.medicionesDe('srv-1'), hasLength(1));
    expect(await repo.pendingCount(), 0);
    expect(await repo.rejectedCount(), 0);
    // El servidor recibió la medición y la confirmación bajo la vaca del servidor.
    expect(server.mediciones.values.single['vaca_id'], 'srv-1');
    expect(server.confirmaciones, hasLength(1));
  });

  group('actualización del modelo', () {
    Future<(Uint8List, Map<String, dynamic>)> newModel() async {
      final json = jsonDecode(readModelsFile('model_lite.json')) as Map<String, dynamic>;
      json['model_version'] = 'mastitis-B-lr-nuevo';
      json['intercept'] = (json['intercept'] as num).toDouble() + 0.5;
      final bytes = Uint8List.fromList(utf8.encode(jsonEncode(json)));
      return (bytes, json);
    }

    test('descarga y reemplaza cuando el hash coincide', () async {
      final (bytes, _) = await newModel();
      server.liteBytes = bytes;
      server.manifestJson = {
        'model_version': 'mastitis-B-lr-nuevo',
        'files': {'model_lite.json': _sha(bytes)},
      };
      final report = await service.syncNow();
      expect(report.modelUpdatedTo, 'mastitis-B-lr-nuevo');
      expect(store.current.version, 'mastitis-B-lr-nuevo');

      // Persistió: un nuevo ModelStore sobre la misma base lo recupera.
      final reloaded = ModelStore(repo, assetLoader: () async => readModelsFile('model_lite.json'));
      expect((await reloaded.load()).version, 'mastitis-B-lr-nuevo');
    });

    test('rechaza un modelo cuyo hash no coincide y conserva el actual', () async {
      final (bytes, _) = await newModel();
      final before = store.current.version;
      server.liteBytes = bytes;
      server.manifestJson = {
        'model_version': 'mastitis-B-lr-nuevo',
        'files': {'model_lite.json': 'deadbeef'},
      };
      final report = await service.syncNow();
      expect(report.ok, isTrue, reason: 'el push/pull no se invalida por un modelo malo');
      expect(report.modelError, contains('hash'));
      expect(store.current.version, before);
    });

    test('rechaza un modelo corrupto aunque el hash coincida', () async {
      final bytes = Uint8List.fromList(utf8.encode('{"no": "es un modelo"}'));
      server.liteBytes = bytes;
      server.manifestJson = {
        'model_version': 'x',
        'files': {'model_lite.json': _sha(bytes)},
      };
      final before = store.current.version;
      final report = await service.syncNow();
      expect(report.modelError, isNotNull);
      expect(store.current.version, before);
    });
  });
}

String _sha(Uint8List bytes) => sha256Hex(bytes);

// (ModelStore) prioridad del asset tras actualizar la app
