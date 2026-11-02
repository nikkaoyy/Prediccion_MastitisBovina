import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/entities.dart';
import '../state/app_state.dart';

/// Registro de la prueba CMT que confirma (o no) la estimación del modelo.
class CmtScreen extends StatefulWidget {
  const CmtScreen({super.key, required this.medicionId});
  final String medicionId;

  @override
  State<CmtScreen> createState() => _CmtScreenState();
}

class _CmtScreenState extends State<CmtScreen> {
  CmtGrade? _grade;
  bool _blind = false;
  final _evaluador = TextEditingController();
  bool _saving = false;

  @override
  void dispose() {
    _evaluador.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final grade = _grade;
    if (grade == null) return;
    final app = context.read<AppState>();
    setState(() => _saving = true);
    await app.repo.registrarConfirmacion(
      medicionId: widget.medicionId,
      grado: grade,
      evaluador: _evaluador.text,
      ciegoAlPh: _blind,
    );
    await app.dataChanged();
    if (mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Prueba CMT')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const Text('Resultado de la prueba de California (CMT) en este animal:'),
        const SizedBox(height: 12),
        RadioGroup<CmtGrade>(
          groupValue: _grade,
          onChanged: (v) => setState(() => _grade = v),
          child: Column(children: [
            for (final g in CmtGrade.values)
              RadioListTile<CmtGrade>(
                value: g,
                title: Text(g.label),
                subtitle: Text(g.positive ? 'Positivo' : 'Negativo'),
              ),
          ]),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _evaluador,
          decoration: const InputDecoration(labelText: 'Quién hizo la prueba (opcional)'),
        ),
        CheckboxListTile(
          value: _blind,
          onChanged: (v) => setState(() => _blind = v ?? false),
          title: const Text('La persona NO conocía el pH ni la estimación al leer el CMT'),
          controlAffinity: ListTileControlAffinity.leading,
        ),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: (_grade == null || _saving) ? null : _save,
          child: const Text('Guardar resultado'),
        ),
      ]),
    );
  }
}
