import 'dart:convert';

import 'package:crypto/crypto.dart';

import '../data/repository.dart';
import '../models/lite_model.dart';
import 'model_store.dart';
import 'sync_api.dart';

class SyncReport {
  SyncReport(this.at);
  final DateTime at;
  int accepted = 0;
  int duplicates = 0;
  int rejected = 0;
  int retried = 0;
  int pulled = 0;
  String? modelUpdatedTo;
  String? error;
  String? modelError;
  bool unauthorized = false;

  bool get ok => error == null;

  String get summary {
    if (error != null) return error!;
    final parts = <String>[
      if (accepted + duplicates > 0) '${accepted + duplicates} enviados',
      if (pulled > 0) '$pulled recibidos',
      if (rejected > 0) '$rejected rechazados',
      if (retried > 0) '$retried pendientes de dependencia',
      if (modelUpdatedTo != null) 'modelo actualizado',
      if (modelError != null) 'modelo: $modelError',
    ];
    return parts.isEmpty ? 'Todo al día' : parts.join(' · ');
  }
}

/// Sincronización asíncrona offline-first:
/// 1) push de pendientes (idempotente) 2) pull por cursores 3) actualiza el modelo.
/// Un fallo de red nunca borra ni modifica registros locales pendientes.
class SyncService {
  SyncService({
    required this.repo,
    required this.apiFactory,
    required this.modelStore,
    this.batchSize = 200,
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  final Repository repo;
  final Future<SyncApi?> Function() apiFactory;
  final ModelStore modelStore;
  final int batchSize;
  final DateTime Function() _clock;

  Future<SyncReport> syncNow() async {
    final report = SyncReport(_clock());
    final api = await apiFactory();
    if (api == null) {
      report.error = 'Servidor no configurado';
      return report;
    }
    try {
      return await _run(api, report);
    } finally {
      api.close();
    }
  }

  Future<SyncReport> _run(SyncApi api, SyncReport report) async {

    try {
      await _push(api, report);
      await _pull(api, report);
      // Si el pull reasignó vacas (arete duplicado), hay registros pendientes de nuevo.
      if (report.pulled > 0 && await repo.pendingCount() > 0) await _push(api, report);
      await repo.setMeta('last_sync_at', _clock().toUtc().toIso8601String());
    } on NetworkException catch (e) {
      report.error = e.message;
      return report;
    } on ApiException catch (e) {
      report.error = e.message;
      report.unauthorized = e.unauthorized;
      return report;
    }

    try {
      await _updateModel(api, report);
    } on NetworkException catch (e) {
      report.modelError = e.message;
    } on ApiException catch (e) {
      report.modelError = e.message;
    } on FormatException catch (e) {
      report.modelError = 'modelo inválido (${e.message})';
    }
    return report;
  }

  Future<void> _push(SyncApi api, SyncReport report) async {
    // Tope defensivo para no ciclar si el servidor responde algo inesperado.
    for (var round = 0; round < 1000; round++) {
      final batch = await repo.pendingBatch(limit: batchSize);
      if (batch.isEmpty) return;

      final response = await api.push(batch.toApi());
      final results = (response['results'] as Map<String, dynamic>?) ?? const {};

      var changed = 0;
      for (final kind in SyncKind.values) {
        final list = (results[kind.name] as List?) ?? const [];
        changed += await repo.applyResults(kind, list);
        for (final raw in list) {
          switch ((raw as Map<String, dynamic>)['status']) {
            case 'accepted':
              report.accepted++;
            case 'duplicate':
              report.duplicates++;
            case 'rejected':
              report.rejected++;
            case 'retry':
              report.retried++;
          }
        }
      }
      // Solo hay 'retry': falta una dependencia; se reintenta en la próxima sincronización.
      if (changed == 0) return;
    }
  }

  Future<void> _pull(SyncApi api, SyncReport report) async {
    var cursors = {
      for (final kind in SyncKind.values)
        kind.name: int.tryParse(await repo.getMeta('cursor_${kind.name}') ?? '') ?? 0,
    };

    for (var page = 0; page < 10000; page++) {
      final response = await api.pull(
        cursorVacas: cursors['vacas']!,
        cursorMediciones: cursors['mediciones']!,
        cursorConfirmaciones: cursors['confirmaciones']!,
      );

      report.pulled += await repo.mergeFromServer(
        vacas: response['vacas'] as List? ?? const [],
        mediciones: response['mediciones'] as List? ?? const [],
        confirmaciones: response['confirmaciones'] as List? ?? const [],
      );

      final next = response['cursors'] as Map<String, dynamic>;
      cursors = {for (final kind in SyncKind.values) kind.name: next[kind.name] as int};
      for (final kind in SyncKind.values) {
        await repo.setMeta('cursor_${kind.name}', '${cursors[kind.name]}');
      }
      if (response['has_more'] != true) return;
    }
  }

  Future<void> _updateModel(SyncApi api, SyncReport report) async {
    final manifest = await api.manifest();
    final remoteVersion = manifest['model_version'] as String;
    if (remoteVersion == modelStore.current.version) return;

    final bytes = await api.downloadLite();
    final expected = (manifest['files'] as Map<String, dynamic>)['model_lite.json'] as String;
    if (sha256.convert(bytes).toString() != expected) {
      throw ApiException('El modelo descargado no coincide con el hash del manifiesto');
    }
    final json = utf8.decode(bytes);
    final candidate = LiteModel.fromJsonString(json); // valida estructura
    if (candidate.version != remoteVersion) {
      throw const FormatException('la versión del modelo no coincide con el manifiesto');
    }
    await modelStore.replace(json);
    report.modelUpdatedTo = candidate.version;
  }
}
