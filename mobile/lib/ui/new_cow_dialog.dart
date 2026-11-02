import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/repository.dart';
import '../state/app_state.dart';

Future<void> showNewCowDialog(BuildContext context) async {
  final app = context.read<AppState>();
  final arete = TextEditingController();
  final nombre = TextEditingController();
  final formKey = GlobalKey<FormState>();
  String? serverError;

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('Nueva vaca'),
        content: Form(
          key: formKey,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextFormField(
              controller: arete,
              decoration: const InputDecoration(labelText: 'Número de arete *'),
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Obligatorio' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: nombre,
              decoration: const InputDecoration(labelText: 'Nombre (opcional)'),
            ),
            if (serverError != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(serverError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancelar')),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(120, 48)),
            onPressed: () async {
              if (!formKey.currentState!.validate()) return;
              try {
                await app.repo.crearVaca(arete: arete.text, nombre: nombre.text);
                await app.dataChanged();
                if (dialogContext.mounted) Navigator.pop(dialogContext);
              } on DuplicateAreteException catch (e) {
                setState(() => serverError = e.toString());
              }
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    ),
  );
}
