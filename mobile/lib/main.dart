import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'data/app_database.dart';
import 'data/repository.dart';
import 'state/app_state.dart';
import 'sync/model_store.dart';
import 'sync/sync_controller.dart';
import 'sync/sync_service.dart';
import 'ui/home_screen.dart';
import 'ui/theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final db = await AppDatabase.open();
  final repo = Repository(db);
  final modelStore = ModelStore(repo);
  await modelStore.load();

  late final AppState state;
  final service = SyncService(
    repo: repo,
    modelStore: modelStore,
    apiFactory: () => apiFromSettings(repo),
  );
  final controller = SyncController(
    repo: repo,
    service: service,
    onlineChanges: Connectivity()
        .onConnectivityChanged
        .map((results) => results.any((r) => r != ConnectivityResult.none)),
    onModelUpdated: () => state.reloadModel(),
  );
  state = AppState(repo: repo, modelStore: modelStore, sync: controller);

  runApp(MastitisApp(state: state));
  await controller.start();
}

class MastitisApp extends StatelessWidget {
  const MastitisApp({super.key, required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider<AppState>.value(
        value: state,
        child: MaterialApp(
          title: 'Mastitis',
          debugShowCheckedModeBanner: false,
          theme: buildTheme(),
          home: const HomeScreen(),
        ),
      );
}
