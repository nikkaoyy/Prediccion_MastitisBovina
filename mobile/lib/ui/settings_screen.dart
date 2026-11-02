import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _url = TextEditingController();
  final _token = TextEditingController();
  bool _loaded = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loaded) return;
    _loaded = true;
    final repo = context.read<AppState>().repo;
    repo.getMeta('server_url').then((v) => _url.text = v ?? '');
    repo.getMeta('device_token').then((v) => _token.text = v ?? '');
  }

  @override
  void dispose() {
    _url.dispose();
    _token.dispose();
    super.dispose();
  }

  Future<void> _saveAndSync() async {
    final app = context.read<AppState>();
    await app.repo.setMeta('server_url', _url.text.trim());
    await app.repo.setMeta('device_token', _token.text.trim());
    await app.sync.syncNow();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final sync = app.sync;
    final report = sync.lastReport;

    return Scaffold(
      appBar: AppBar(title: const Text('Configuración')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Servidor', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _url,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(labelText: 'Dirección (https://...)'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _token,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'Código del dispositivo'),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: sync.syncing ? null : _saveAndSync,
          icon: sync.syncing
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.sync),
          label: Text(sync.syncing ? 'Sincronizando…' : 'Guardar y sincronizar'),
        ),
        const SizedBox(height: 20),
        ListTile(
          leading: Icon(report == null || report.ok ? Icons.check_circle_outline : Icons.error_outline),
          title: Text(report == null ? 'Aún no se ha sincronizado' : report.summary),
          subtitle: report == null ? null : Text(formatDateTime(report.at)),
        ),
        ListTile(
          leading: const Icon(Icons.cloud_upload_outlined),
          title: Text('${sync.pending} registro(s) por enviar'),
          subtitle: sync.rejected > 0 ? Text('${sync.rejected} rechazado(s) por el servidor') : null,
        ),
        ListTile(
          leading: const Icon(Icons.memory),
          title: const Text('Modelo de riesgo'),
          subtitle: Text(app.model.version),
        ),
        const SizedBox(height: 8),
        const Text(decisionSupportNotice),
      ]),
    );
  }
}
