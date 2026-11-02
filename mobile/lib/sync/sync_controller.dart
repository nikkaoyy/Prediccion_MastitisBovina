import 'dart:async';

import 'package:flutter/foundation.dart';

import '../data/repository.dart';
import 'sync_api.dart';
import 'sync_service.dart';

/// Orquesta cuándo sincronizar: al abrir, al recuperar conexión y cada [interval].
class SyncController extends ChangeNotifier {
  SyncController({
    required this.repo,
    required this.service,
    required this.onlineChanges,
    this.interval = const Duration(minutes: 15),
    this.onModelUpdated,
  });

  final Repository repo;
  final SyncService service;
  final Stream<bool> onlineChanges;
  final Duration interval;
  final VoidCallback? onModelUpdated;

  bool syncing = false;
  bool online = true;
  SyncReport? lastReport;
  int pending = 0;
  int rejected = 0;

  StreamSubscription<bool>? _sub;
  Timer? _timer;

  Future<void> start() async {
    await refreshCounts();
    _sub = onlineChanges.listen((isOnline) {
      final regained = isOnline && !online;
      online = isOnline;
      notifyListeners();
      if (regained) unawaited(syncNow());
    });
    _timer = Timer.periodic(interval, (_) => unawaited(syncNow()));
    unawaited(syncNow());
  }

  Future<void> refreshCounts() async {
    pending = await repo.pendingCount();
    rejected = await repo.rejectedCount();
    notifyListeners();
  }

  Future<SyncReport?> syncNow() async {
    if (syncing) return lastReport;
    syncing = true;
    notifyListeners();
    try {
      final report = await service.syncNow();
      lastReport = report;
      if (report.modelUpdatedTo != null) onModelUpdated?.call();
      return report;
    } on Object catch (e) {
      // Cualquier fallo inesperado se informa sin perder datos locales.
      final report = SyncReport(DateTime.now())..error = 'Error inesperado: $e';
      lastReport = report;
      return report;
    } finally {
      syncing = false;
      await refreshCounts();
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    _timer?.cancel();
    super.dispose();
  }
}

/// Fábrica de [SyncApi] a partir de la configuración guardada (URL + token).
Future<SyncApi?> apiFromSettings(Repository repo) async {
  final url = (await repo.getMeta('server_url'))?.trim() ?? '';
  final token = (await repo.getMeta('device_token'))?.trim() ?? '';
  if (url.isEmpty || token.isEmpty) return null;
  return HttpSyncApi(baseUrl: url, token: token);
}
