import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:mastitis_app/sync/model_store.dart';

import 'helpers.dart';

String modelWithVersion(String version) {
  final json = jsonDecode(readModelsFile('model_lite.json')) as Map<String, dynamic>;
  json['model_version'] = version;
  return jsonEncode(json);
}

void main() {
  test('el modelo descargado se conserva mientras no cambie el asset de la app', () async {
    final (_, repo, _) = await openTestRepo();
    final asset = modelWithVersion('asset-v1');
    final store = ModelStore(repo, assetLoader: () async => asset);
    await store.load();
    await store.replace(modelWithVersion('server-v2'));

    final reopened = ModelStore(repo, assetLoader: () async => asset);
    expect((await reopened.load()).version, 'server-v2');
  });

  test('si la app se actualiza con otro asset, se descarta el modelo guardado', () async {
    final (_, repo, _) = await openTestRepo();
    final oldAsset = modelWithVersion('asset-v1');
    final store = ModelStore(repo, assetLoader: () async => oldAsset);
    await store.load();
    await store.replace(modelWithVersion('server-v2'));

    final newApp = ModelStore(repo, assetLoader: () async => modelWithVersion('asset-v3'));
    expect((await newApp.load()).version, 'asset-v3');
    expect(await repo.getMeta(ModelStore.metaKey), isNull);
  });

  test('un modelo guardado dañado cae al empaquetado', () async {
    final (_, repo, _) = await openTestRepo();
    final asset = modelWithVersion('asset-v1');
    await repo.setMeta(ModelStore.metaKey, '{roto');
    await repo.setMeta(ModelStore.assetVersionKey, 'asset-v1');
    final store = ModelStore(repo, assetLoader: () async => asset);
    expect((await store.load()).version, 'asset-v1');
  });
}
