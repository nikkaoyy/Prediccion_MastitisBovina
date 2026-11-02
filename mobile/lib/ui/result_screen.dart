import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/entities.dart';
import '../state/app_state.dart';
import 'cmt_screen.dart';
import 'theme.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.medicionId, this.justSaved = false});
  final String medicionId;
  final bool justSaved;

  Future<(Medicion?, Confirmacion?)> _load(AppState app) async =>
      (await app.repo.medicion(medicionId), await app.repo.confirmacionDe(medicionId));

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return FutureBuilder<(Medicion?, Confirmacion?)>(
      future: _load(app),
      builder: (context, snapshot) {
        final medicion = snapshot.data?.$1;
        final confirmacion = snapshot.data?.$2;
        return Scaffold(
          appBar: AppBar(title: const Text('Resultado')),
          body: medicion == null
              ? const Center(child: CircularProgressIndicator())
              : ListView(padding: const EdgeInsets.all(16), children: [
                  _RiskCard(medicion: medicion),
                  const SizedBox(height: 16),
                  Text(recommendationFor(medicion.nivelRiesgo),
                      style: Theme.of(context).textTheme.bodyLarge),
                  const SizedBox(height: 16),
                  Card(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    child: const Padding(
                      padding: EdgeInsets.all(14),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Icon(Icons.info_outline),
                        SizedBox(width: 10),
                        Expanded(child: Text(decisionSupportNotice)),
                      ]),
                    ),
                  ),
                  const SizedBox(height: 16),
                  if (confirmacion != null)
                    ListTile(
                      leading: Icon(confirmacion.resultadoPositivo ? Icons.science : Icons.science_outlined),
                      title: Text('CMT: ${confirmacion.grado?.label ?? (confirmacion.resultadoPositivo ? 'Positivo' : 'Negativo')}'),
                      subtitle: Text(formatDateTime(confirmacion.fecha)),
                    )
                  else
                    FilledButton.icon(
                      icon: const Icon(Icons.science_outlined),
                      label: const Text('Registrar prueba CMT'),
                      onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                          builder: (_) => CmtScreen(medicionId: medicion.id))),
                    ),
                  const SizedBox(height: 12),
                  Text(
                    'Puntaje del modelo: ${medicion.probabilidad.toStringAsFixed(2)} '
                    '(no es una probabilidad calibrada) · modelo ${medicion.modelVersion}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (medicion.syncState == SyncState.rejected)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text('El servidor rechazó este registro: ${medicion.syncError ?? ''}',
                          style: TextStyle(color: Theme.of(context).colorScheme.error)),
                    ),
                  if (justSaved)
                    Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Listo'),
                      ),
                    ),
                ]),
        );
      },
    );
  }
}

class _RiskCard extends StatelessWidget {
  const _RiskCard({required this.medicion});
  final Medicion medicion;

  @override
  Widget build(BuildContext context) {
    final style = RiskStyle.of(medicion.nivelRiesgo);
    return Semantics(
      label: style.label,
      child: Card(
        color: style.background,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(children: [
            Icon(style.icon, size: 64, color: style.foreground),
            const SizedBox(height: 8),
            Text(style.label,
                style: Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(color: style.foreground, fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text('pH ${medicion.phLeche.toStringAsFixed(2)} · ${formatDateTime(medicion.fecha)}',
                style: TextStyle(color: style.foreground)),
          ]),
        ),
      ),
    );
  }
}
