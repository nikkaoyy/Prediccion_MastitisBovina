import 'package:flutter/foundation.dart';

import '../data/repository.dart';
import '../models/lite_model.dart';
import '../sync/model_store.dart';
import '../sync/sync_controller.dart';

/// Estado global de la app: repositorio, modelo vigente y sincronización.
class AppState extends ChangeNotifier {
  AppState({required this.repo, required this.modelStore, required this.sync}) {
    sync.addListener(notifyListeners);
  }

  final Repository repo;
  final ModelStore modelStore;
  final SyncController sync;

  LiteModel get model => modelStore.current;

  /// Tras guardar datos localmente: refresca contadores y listas.
  Future<void> dataChanged() async {
    await sync.refreshCounts();
    notifyListeners();
  }

  Future<void> reloadModel() async {
    await modelStore.load();
    notifyListeners();
  }

  @override
  void dispose() {
    sync.removeListener(notifyListeners);
    super.dispose();
  }
}
