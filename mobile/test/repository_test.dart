import 'package:flutter_test/flutter_test.dart';
import 'package:mastitis_app/data/repository.dart';
import 'package:mastitis_app/models/entities.dart';
import 'package:mastitis_app/models/lite_model.dart';

import 'helpers.dart';

MedicionInput input({double ph = 6.9}) => MedicionInput(
      edad: 5, raza: 'Holstein', numeroDePartos: 3, etapaDeLactancia: 1,
      antecedentesDeMastitis: 0, phLeche: ph,
    );

void main() {
  late Repository repo;
  late LiteModel model;

  setUp(() async {
    final opened = await openTestRepo();
    repo = opened.$2;
    model = opened.$3.current;
  });

  test('crea vacas, rechaza arete duplicado y exige arete', () async {
    final v = await repo.crearVaca(arete: ' A-1 ', nombre: ' Lola ');
    expect(v.arete, 'A-1');
    expect(v.nombre, 'Lola');
    await expectLater(repo.crearVaca(arete: 'A-1'), throwsA(isA<DuplicateAreteException>()));
    await expectLater(repo.crearVaca(arete: '  '), throwsArgumentError);
    expect((await repo.vacas()).length, 1);
  });

  test('registrar medición calcula riesgo, queda pendiente y valida pH', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    final m = await repo.registrarMedicion(vacaId: v.id, input: input(ph: 7.1), model: model);
    expect(m.nivelRiesgo, RiskLevel.alto);
    expect(m.modelVersion, model.version);
    expect(m.syncState, SyncState.pending);

    await expectLater(
        repo.registrarMedicion(vacaId: v.id, input: input(ph: 11), model: model), throwsArgumentError);
    expect((await repo.medicionesDe(v.id)).length, 1);

    final resumen = (await repo.vacas()).single;
    expect(resumen.ultimoNivel, RiskLevel.alto);
  });

  test('lote pendiente respeta orden vacas → mediciones → confirmaciones y el límite', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    final m = await repo.registrarMedicion(vacaId: v.id, input: input(), model: model);
    await repo.registrarConfirmacion(medicionId: m.id, grado: CmtGrade.dos, ciegoAlPh: true);

    final all = await repo.pendingBatch();
    expect([all.vacas.length, all.mediciones.length, all.confirmaciones.length], [1, 1, 1]);
    expect(all.confirmaciones.single.resultadoPositivo, isTrue);

    final limited = await repo.pendingBatch(limit: 2);
    expect([limited.vacas.length, limited.mediciones.length, limited.confirmaciones.length], [1, 1, 0]);
    expect(await repo.pendingCount(), 3);
  });

  test('si el servidor rechaza la vaca, sus hijos pendientes se marcan rechazados', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    final m = await repo.registrarMedicion(vacaId: v.id, input: input(), model: model);
    await repo.registrarConfirmacion(medicionId: m.id, grado: CmtGrade.n);

    await repo.applyResults(SyncKind.vacas, [
      {'id': v.id, 'status': 'rejected', 'reason': 'arete duplicado en la finca'}
    ]);
    final batch = await repo.pendingBatch();
    expect(batch.isEmpty, isTrue);
    expect(await repo.pendingCount(), 0);
    expect(await repo.rejectedCount(), 3);
  });

  test('applyResults: retry no cambia el estado', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    final changed = await repo.applyResults(SyncKind.vacas, [
      {'id': v.id, 'status': 'retry'}
    ]);
    expect(changed, 0);
    expect(await repo.pendingCount(), 1);
  });

  test('mergeFromServer no pisa registros locales y es idempotente', () async {
    final v = await repo.crearVaca(arete: 'A-1');
    final serverCow = {'id': 'srv-1', 'arete': 'S-9', 'nombre': null};
    final first = await repo.mergeFromServer(vacas: [
      {'id': v.id, 'arete': 'OTRO', 'nombre': 'x'}, // mismo id: se ignora
      serverCow,
    ]);
    expect(first, 1);
    expect(await repo.mergeFromServer(vacas: [serverCow]), 0);
    final cows = await repo.vacas();
    expect(cows.map((c) => c.vaca.arete).toSet(), {'A-1', 'S-9'});
    expect(cows.firstWhere((c) => c.vaca.id == 'srv-1').vaca.syncState, SyncState.synced);
  });
}
