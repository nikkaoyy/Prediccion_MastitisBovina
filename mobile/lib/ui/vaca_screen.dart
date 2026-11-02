import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/entities.dart';
import '../state/app_state.dart';
import 'measurement_form_screen.dart';
import 'result_screen.dart';
import 'theme.dart';

class VacaScreen extends StatelessWidget {
  const VacaScreen({super.key, required this.vacaId});
  final String vacaId;

  Future<(Vaca?, List<Medicion>)> _load(AppState app) async =>
      (await app.repo.vaca(vacaId), await app.repo.medicionesDe(vacaId));

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return FutureBuilder<(Vaca?, List<Medicion>)>(
      future: _load(app),
      builder: (context, snapshot) {
        final vaca = snapshot.data?.$1;
        final mediciones = snapshot.data?.$2 ?? const <Medicion>[];
        return Scaffold(
          appBar: AppBar(title: Text(vaca?.titulo ?? 'Vaca')),
          body: snapshot.connectionState != ConnectionState.done
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    FilledButton.icon(
                      icon: const Icon(Icons.science_outlined),
                      label: const Text('Nueva medición'),
                      onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                          builder: (_) => MeasurementFormScreen(vacaId: vacaId))),
                    ),
                    const SizedBox(height: 20),
                    Text('Historial', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    if (mediciones.isEmpty) const Text('Sin mediciones todavía.'),
                    for (final m in mediciones) _MeasurementTile(medicion: m),
                  ],
                ),
        );
      },
    );
  }
}

class _MeasurementTile extends StatelessWidget {
  const _MeasurementTile({required this.medicion});
  final Medicion medicion;

  @override
  Widget build(BuildContext context) {
    final style = RiskStyle.of(medicion.nivelRiesgo);
    final synced = switch (medicion.syncState) {
      SyncState.synced => (Icons.cloud_done_outlined, 'Enviado'),
      SyncState.pending => (Icons.cloud_upload_outlined, 'Por enviar'),
      SyncState.rejected => (Icons.report_problem_outlined, 'Rechazado'),
    };
    return Card(
      child: ListTile(
        leading: Icon(style.icon, color: style.foreground),
        title: Text('${style.label} · pH ${medicion.phLeche.toStringAsFixed(2)}'),
        subtitle: Text(formatDateTime(medicion.fecha)),
        trailing: Tooltip(message: synced.$2, child: Icon(synced.$1)),
        onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => ResultScreen(medicionId: medicion.id))),
      ),
    );
  }
}
