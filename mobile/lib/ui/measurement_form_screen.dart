import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/entities.dart';
import '../state/app_state.dart';
import 'result_screen.dart';

double? parseDecimal(String? text) {
  if (text == null) return null;
  final clean = text.trim().replaceAll(',', '.');
  if (clean.isEmpty) return null;
  final value = double.tryParse(clean);
  // 'NaN' e 'Infinity' se parsean pero no son mediciones válidas.
  return (value != null && value.isFinite) ? value : null;
}

class MeasurementFormScreen extends StatefulWidget {
  const MeasurementFormScreen({super.key, required this.vacaId});
  final String vacaId;

  @override
  State<MeasurementFormScreen> createState() => _MeasurementFormScreenState();
}

class _MeasurementFormScreenState extends State<MeasurementFormScreen> {
  static const otherBreed = 'Otra';

  final _formKey = GlobalKey<FormState>();
  final _edad = TextEditingController();
  final _partos = TextEditingController();
  final _ph = TextEditingController();
  final _volumen = TextEditingController();
  final _humedad = TextEditingController();
  final _temperatura = TextEditingController();
  String? _raza;
  int _etapa = 0;
  int _antecedentes = 0;
  bool _saving = false;

  @override
  void dispose() {
    for (final c in [_edad, _partos, _ph, _volumen, _humedad, _temperatura]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _required(String? v) => (v == null || v.trim().isEmpty) ? 'Obligatorio' : null;

  String? _intField(String? v, {required double min, required double max, required String name}) {
    if (_required(v) != null) return 'Obligatorio';
    final n = int.tryParse(v!.trim());
    if (n == null) return 'Escriba un número entero';
    if (n < min || n > max) return '$name debe estar entre ${min.toInt()} y ${max.toInt()}';
    return null;
  }

  String? _optionalDecimal(String? v, String key) {
    if (v == null || v.trim().isEmpty) return null;
    final n = parseDecimal(v);
    if (n == null) return 'Escriba un número';
    final range = context.read<AppState>().model.ranges[key];
    if (range != null && (n < range.low || n > range.high)) {
      return 'Debe estar entre ${range.low} y ${range.high}';
    }
    return null;
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    final app = context.read<AppState>();
    setState(() => _saving = true);
    try {
      final medicion = await app.repo.registrarMedicion(
        vacaId: widget.vacaId,
        model: app.model,
        input: MedicionInput(
          edad: int.parse(_edad.text.trim()),
          raza: _raza!,
          numeroDePartos: int.parse(_partos.text.trim()),
          volumenDeLeche: parseDecimal(_volumen.text),
          etapaDeLactancia: _etapa,
          antecedentesDeMastitis: _antecedentes,
          humedad: parseDecimal(_humedad.text),
          temperatura: parseDecimal(_temperatura.text),
          phLeche: parseDecimal(_ph.text)!,
        ),
      );
      await app.dataChanged();
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
          builder: (_) => ResultScreen(medicionId: medicion.id, justSaved: true)));
    } on ArgumentError catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${e.message}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = context.watch<AppState>().model;
    final breeds = [...model.breeds, otherBreed];
    final phRange = model.ranges['ph_leche'];

    return Scaffold(
      appBar: AppBar(title: const Text('Nueva medición')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _ph,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'pH de la leche *',
                helperText: 'Mida la muestra con el pHmetro calibrado. Es el dato más importante.',
              ),
              validator: (v) {
                if (_required(v) != null) return 'Obligatorio: sin pH no se puede estimar el riesgo';
                final n = parseDecimal(v);
                if (n == null) return 'Escriba un número (ej. 6.7)';
                if (phRange != null && (n < phRange.low || n > phRange.high)) {
                  return 'Valor fuera de rango (${phRange.low} a ${phRange.high})';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _edad,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Edad (años) *'),
              validator: (v) => _intField(v, min: 1, max: 25, name: 'La edad'),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _raza,
              decoration: const InputDecoration(labelText: 'Raza *'),
              items: [for (final b in breeds) DropdownMenuItem(value: b, child: Text(b.replaceAll('_', ' ')))],
              onChanged: (v) => setState(() => _raza = v),
              validator: (v) => v == null ? 'Obligatorio' : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _partos,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Número de partos *'),
              validator: (v) => _intField(v, min: 0, max: 20, name: 'Los partos'),
            ),
            const SizedBox(height: 16),
            Text('Etapa de lactancia *', style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 6),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('Temprana')),
                ButtonSegment(value: 1, label: Text('Tardía')),
              ],
              selected: {_etapa},
              onSelectionChanged: (s) => setState(() => _etapa = s.first),
            ),
            const SizedBox(height: 16),
            Text('¿Ha tenido mastitis antes? *', style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 6),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 0, label: Text('No')),
                ButtonSegment(value: 1, label: Text('Sí')),
              ],
              selected: {_antecedentes},
              onSelectionChanged: (s) => setState(() => _antecedentes = s.first),
            ),
            const SizedBox(height: 24),
            Text('Opcionales', style: Theme.of(context).textTheme.titleMedium),
            const Text('Si los deja vacíos, el modelo usa un valor típico y la estimación es menos precisa.'),
            const SizedBox(height: 12),
            TextFormField(
              controller: _volumen,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Leche del día (litros)'),
              validator: (v) => _optionalDecimal(v, 'volumen_de_leche'),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _temperatura,
              keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
              decoration: const InputDecoration(labelText: 'Temperatura ambiente (°C)'),
              validator: (v) => _optionalDecimal(v, 'temperatura'),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _humedad,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Humedad relativa (%)'),
              validator: (v) => _optionalDecimal(v, 'humedad'),
            ),
            const SizedBox(height: 28),
            FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: const Icon(Icons.calculate_outlined),
              label: const Text('Calcular riesgo'),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
