// Prueba de extremo a extremo contra un servidor FastAPI real.
// Se ejecuta con: python scripts/e2e_local.py  (levanta el servidor y exporta las variables).
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:mastitis_app/data/repository.dart';
import 'package:mastitis_app/models/entities.dart';
import 'package:mastitis_app/sync/model_store.dart';
import 'package:mastitis_app/sync/sync_api.dart';
import 'package:mastitis_app/sync/sync_service.dart';

import '../helpers.dart';

void main() {
  final url = Platform.environment['E2E_SERVER_URL'];
  final token = Platform.environment['E2E_TOKEN'];
  final outPath = Platform.environment['E2E_OUT'];
  final skip = (url == null || token == null)
      ? 'Defina E2E_SERVER_URL y E2E_TOKEN (use scripts/e2e_local.py)'
      : null;

  Future<(Repository, ModelStore)> phone() async {
    final (_, repo, store) = await openTestRepo();
    return (repo, store);
  }

  MedicionInput input(double ph) => MedicionInput(
        edad: 5, raza: 'Holstein', numeroDePartos: 3, etapaDeLactancia: 1,
        antecedentesDeMastitis: 0, phLeche: ph,
      );

  test('offline → online → reenvío → segundo teléfono, sin pérdidas ni duplicados', () async {
    final (repo, store) = await phone();

    final expected = <String>{};
    for (var i = 0; i < 3; i++) {
      final vaca = await repo.crearVaca(arete: 'E2E-$i', nombre: 'Vaca $i');
      expected.add(vaca.id);
      for (var j = 0; j < 2; j++) {
        final m = await repo.registrarMedicion(
            vacaId: vaca.id, input: input(6.5 + 0.3 * j + 0.1 * i), model: store.current);
        expected.add(m.id);
        if (j == 0) {
          final c = await repo.registrarConfirmacion(
              medicionId: m.id, grado: i.isEven ? CmtGrade.dos : CmtGrade.n, ciegoAlPh: true);
          expected.add(c.id);
        }
      }
    }
    expect(expected.length, 12);
    expect(await repo.pendingCount(), 12);

    // 1) Sin servidor alcanzable (puerto cerrado): nada se pierde.
    final offline = SyncService(
      repo: repo, modelStore: store, batchSize: 5,
      apiFactory: () async => HttpSyncApi(
          baseUrl: 'http://127.0.0.1:1', token: token!, timeout: const Duration(seconds: 3)),
    );
    final failed = await offline.syncNow();
    expect(failed.ok, isFalse);
    expect(await repo.pendingCount(), 12);

    // 2) Con servidor: todo se envía, en lotes de 5.
    final online = SyncService(
      repo: repo, modelStore: store, batchSize: 5,
      apiFactory: () async => HttpSyncApi(baseUrl: url!, token: token!),
    );
    final report = await online.syncNow();
    expect(report.ok, isTrue, reason: report.summary);
    expect(report.accepted, 12);
    expect(report.rejected, 0);
    expect(await repo.pendingCount(), 0);

    // 3) La respuesta se "perdió": todo vuelve a pendiente y se reenvía → duplicados.
    for (final t in ['vacas', 'mediciones', 'confirmaciones']) {
      await repo.db.update(t, {'sync_state': 'pending'});
    }
    final replay = await online.syncNow();
    expect(replay.ok, isTrue, reason: replay.summary);
    expect(replay.duplicates, 12);
    expect(replay.accepted, 0);
    expect(await repo.pendingCount(), 0);

    // 4) Un segundo teléfono (misma finca) recupera todo con pull.
    final (repo2, store2) = await phone();
    final second = SyncService(
      repo: repo2, modelStore: store2,
      apiFactory: () async => HttpSyncApi(baseUrl: url!, token: token!),
    );
    final pulled = await second.syncNow();
    expect(pulled.ok, isTrue, reason: pulled.summary);
    expect(pulled.pulled, 12);
    expect((await repo2.vacas()).length, 3);

    // 5) El modelo del servidor coincide con el empaquetado: no hay actualización.
    expect(report.modelUpdatedTo, isNull);

    if (outPath != null) {
      File(outPath).writeAsStringSync(jsonEncode({'ids': expected.toList()..sort()}));
    }
  }, skip: skip, timeout: const Timeout(Duration(minutes: 2)));
}
