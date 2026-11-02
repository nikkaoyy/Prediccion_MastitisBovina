import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/repository.dart';
import '../state/app_state.dart';
import 'new_cow_dialog.dart';
import 'settings_screen.dart';
import 'theme.dart';
import 'vaca_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final sync = app.sync;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mastitis · Mis vacas'),
        actions: [
          IconButton(
            tooltip: 'Configuración y sincronización',
            icon: Badge(
              isLabelVisible: sync.pending > 0,
              label: Text('${sync.pending}'),
              child: Icon(sync.syncing ? Icons.sync : Icons.cloud_sync_outlined),
            ),
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => showNewCowDialog(context),
        icon: const Icon(Icons.add),
        label: const Text('Nueva vaca'),
      ),
      body: Column(
        children: [
          _SyncBanner(app: app),
          Expanded(
            child: FutureBuilder<List<VacaResumen>>(
              future: app.repo.vacas(),
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                final cows = snapshot.data ?? const [];
                if (cows.isEmpty) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(32),
                      child: Text(
                        'Aún no hay vacas registradas.\nToque "Nueva vaca" para empezar. '
                        'Todo se guarda en este teléfono aunque no haya internet.',
                        textAlign: TextAlign.center,
                      ),
                    ),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                  itemCount: cows.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 8),
                  itemBuilder: (context, i) => _CowTile(resumen: cows[i]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _SyncBanner extends StatelessWidget {
  const _SyncBanner({required this.app});
  final AppState app;

  @override
  Widget build(BuildContext context) {
    final sync = app.sync;
    final String text;
    final IconData icon;
    if (!sync.online) {
      text = 'Sin conexión: los datos se guardan en el teléfono (${sync.pending} por enviar).';
      icon = Icons.cloud_off;
    } else if (sync.pending > 0) {
      text = '${sync.pending} registro(s) por sincronizar.';
      icon = Icons.cloud_upload_outlined;
    } else if (sync.rejected > 0) {
      text = '${sync.rejected} registro(s) rechazado(s) por el servidor. Revise Configuración.';
      icon = Icons.report_problem_outlined;
    } else {
      return const SizedBox.shrink();
    }
    return Material(
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(children: [Icon(icon), const SizedBox(width: 10), Expanded(child: Text(text))]),
      ),
    );
  }
}

class _CowTile extends StatelessWidget {
  const _CowTile({required this.resumen});
  final VacaResumen resumen;

  @override
  Widget build(BuildContext context) {
    final vaca = resumen.vaca;
    final level = resumen.ultimoNivel;
    final style = level == null ? null : RiskStyle.of(level);
    return Card(
      child: ListTile(
        minVerticalPadding: 14,
        title: Text(vaca.titulo, style: Theme.of(context).textTheme.titleMedium),
        subtitle: Text(resumen.ultimaFecha == null
            ? 'Sin mediciones'
            : 'Última: ${formatDateTime(resumen.ultimaFecha!)}'),
        leading: Icon(Icons.pets, color: style?.foreground),
        trailing: style == null
            ? null
            : Chip(
                avatar: Icon(style.icon, color: style.foreground, size: 20),
                label: Text(style.label, style: TextStyle(color: style.foreground)),
                backgroundColor: style.background,
              ),
        onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => VacaScreen(vacaId: vaca.id))),
      ),
    );
  }
}
