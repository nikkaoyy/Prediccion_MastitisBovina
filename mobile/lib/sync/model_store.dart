import 'package:flutter/services.dart' show rootBundle;

import '../data/repository.dart';
import '../models/lite_model.dart';

/// Guarda el modelo vigente: el descargado del servidor o, en su defecto,
/// el empaquetado como asset (funciona desde la primera ejecución sin red).
class ModelStore {
  ModelStore(this.repo, {Future<String> Function()? assetLoader})
      : _assetLoader = assetLoader ?? (() => rootBundle.loadString('assets/model_lite.json'));

  static const metaKey = 'lite_model';
  static const assetVersionKey = 'lite_model_asset_version';

  final Repository repo;
  final Future<String> Function() _assetLoader;
  LiteModel? _current;
  LiteModel? _asset;

  LiteModel get current {
    final model = _current;
    if (model == null) throw StateError('ModelStore.load() no se ha ejecutado');
    return model;
  }

  Future<LiteModel> _bundled() async =>
      _asset ??= LiteModel.fromJsonString(await _assetLoader());

  /// Usa el modelo descargado solo si se guardó sobre el mismo asset que trae
  /// esta versión de la app. Si la app se actualizó (otro asset) o el modelo
  /// guardado está dañado, se vuelve al empaquetado y el siguiente sync decide.
  Future<LiteModel> load() async {
    final bundled = await _bundled();
    final stored = await repo.getMeta(metaKey);
    final baseVersion = await repo.getMeta(assetVersionKey);

    if (stored != null && baseVersion == bundled.version) {
      try {
        return _current = LiteModel.fromJsonString(stored);
      } on Object {
        // dañado: se descarta abajo
      }
    }
    if (stored != null) {
      await repo.setMeta(metaKey, null);
      await repo.setMeta(assetVersionKey, null);
    }
    return _current = bundled;
  }

  /// Reemplaza el modelo tras validar que el JSON es un modelo correcto.
  Future<LiteModel> replace(String json) async {
    final model = LiteModel.fromJsonString(json); // lanza si es inválido
    final bundled = await _bundled();
    await repo.setMeta(metaKey, json);
    await repo.setMeta(assetVersionKey, bundled.version);
    return _current = model;
  }
}
