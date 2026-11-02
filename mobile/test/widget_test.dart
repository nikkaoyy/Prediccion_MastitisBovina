import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mastitis_app/models/entities.dart';
import 'package:mastitis_app/state/app_state.dart';
import 'package:mastitis_app/sync/sync_controller.dart';
import 'package:mastitis_app/sync/sync_service.dart';
import 'package:mastitis_app/ui/home_screen.dart';
import 'package:mastitis_app/ui/measurement_form_screen.dart';
import 'package:mastitis_app/ui/theme.dart';
import 'package:provider/provider.dart';

import 'helpers.dart';

/// Deja correr el trabajo real (SQLite en otro isolate) y vuelve a pintar.
Future<void> settle(WidgetTester tester) async {
  for (var i = 0; i < 6; i++) {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 80)));
    await tester.pump(const Duration(milliseconds: 50));
  }
}

Future<(AppState, String)> buildApp(WidgetTester tester) async {
  late AppState app;
  late String vacaId;
  await tester.runAsync(() async {
    final (_, repo, store) = await openTestRepo();
    final sync = SyncController(
      repo: repo,
      service: SyncService(repo: repo, modelStore: store, apiFactory: () async => null),
      onlineChanges: const Stream<bool>.empty(),
    );
    app = AppState(repo: repo, modelStore: store, sync: sync);
    vacaId = (await repo.crearVaca(arete: 'A-1', nombre: 'Lola')).id;
    await app.sync.refreshCounts();
  });
  return (app, vacaId);
}

Widget wrap(AppState app, Widget child) => ChangeNotifierProvider<AppState>.value(
      value: app,
      child: MaterialApp(theme: buildTheme(), home: child),
    );

void main() {
  setUp(() {});

  testWidgets('el formulario exige el pH y muestra por qué', (tester) async {
    tester.view.physicalSize = const Size(900, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final (app, vacaId) = await buildApp(tester);
    await tester.pumpWidget(wrap(app, MeasurementFormScreen(vacaId: vacaId)));

    await tester.tap(find.text('Calcular riesgo'));
    await tester.pump();
    expect(find.textContaining('sin pH no se puede estimar'), findsOneWidget);
    expect(find.text('Obligatorio'), findsWidgets);
  });

  testWidgets('un pH fuera de rango se rechaza y no se guarda nada', (tester) async {
    tester.view.physicalSize = const Size(900, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final (app, vacaId) = await buildApp(tester);
    await tester.pumpWidget(wrap(app, MeasurementFormScreen(vacaId: vacaId)));

    await tester.enterText(find.widgetWithText(TextFormField, 'pH de la leche *'), '12');
    await tester.tap(find.text('Calcular riesgo'));
    await tester.pump();
    expect(find.textContaining('fuera de rango'), findsOneWidget);

    final count = await tester.runAsync(() => app.repo.medicionesDe(vacaId));
    expect(count, isEmpty);
  });

  testWidgets('flujo completo: ingresar datos → riesgo alto con aviso de apoyo a la decisión',
      (tester) async {
    tester.view.physicalSize = const Size(900, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final (app, vacaId) = await buildApp(tester);
    await tester.pumpWidget(wrap(app, MeasurementFormScreen(vacaId: vacaId)));

    await tester.enterText(find.widgetWithText(TextFormField, 'pH de la leche *'), '7,1');
    await tester.enterText(find.widgetWithText(TextFormField, 'Edad (años) *'), '5');
    await tester.enterText(find.widgetWithText(TextFormField, 'Número de partos *'), '3');
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Holstein').last);
    await tester.pumpAndSettle();

    await tester.tap(find.text('Calcular riesgo'));
    await settle(tester);

    expect(find.text('Riesgo alto'), findsOneWidget);
    expect(find.text(decisionSupportNotice), findsOneWidget);
    expect(find.textContaining('no es una probabilidad calibrada'), findsOneWidget);
    expect(find.text('Registrar prueba CMT'), findsOneWidget);

    final saved = await tester.runAsync(() => app.repo.medicionesDe(vacaId));
    expect(saved!.single.phLeche, 7.1, reason: 'la coma decimal se interpreta como punto');
    expect(saved.single.syncState, SyncState.pending);
    expect(app.sync.pending, 2); // la vaca y la medición
  });

  testWidgets('la pantalla principal avisa cuando hay registros por sincronizar', (tester) async {
    final (app, _) = await buildApp(tester);
    await tester.pumpWidget(wrap(app, const HomeScreen()));
    await settle(tester);

    expect(find.textContaining('A-1'), findsOneWidget);
    expect(find.textContaining('por sincronizar'), findsOneWidget);
    expect(find.text('Nueva vaca'), findsOneWidget);
  });

  test('parseDecimal acepta coma y punto', () {
    expect(parseDecimal('6,75'), 6.75);
    expect(parseDecimal(' 6.75 '), 6.75);
    expect(parseDecimal(''), isNull);
    expect(parseDecimal('abc'), isNull);
    expect(parseDecimal('NaN'), isNull);
    expect(parseDecimal('Infinity'), isNull);
  });
}
