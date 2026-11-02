import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../models/entities.dart';
import '../models/lite_model.dart';

class DuplicateAreteException implements Exception {
  DuplicateAreteException(this.arete);
  final String arete;
  @override
  String toString() => 'Ya existe una vaca con el arete "$arete".';
}

enum SyncKind {
  vacas('vacas'),
  mediciones('mediciones'),
  confirmaciones('confirmaciones');

  const SyncKind(this.table);
  final String table;
}

class VacaResumen {
  const VacaResumen(this.vaca, this.ultimoNivel, this.ultimaFecha);
  final Vaca vaca;
  final RiskLevel? ultimoNivel;
  final DateTime? ultimaFecha;
}

class PendingBatch {
  const PendingBatch(this.vacas, this.mediciones, this.confirmaciones);
  final List<Vaca> vacas;
  final List<Medicion> mediciones;
  final List<Confirmacion> confirmaciones;

  bool get isEmpty => vacas.isEmpty && mediciones.isEmpty && confirmaciones.isEmpty;

  Map<String, Object?> toApi() => {
        'vacas': vacas.map((v) => v.toApi()).toList(),
        'mediciones': mediciones.map((m) => m.toApi()).toList(),
        'confirmaciones': confirmaciones.map((c) => c.toApi()).toList(),
      };
}

/// Acceso a datos local. Todo registro se guarda como `pending` hasta que el
/// servidor lo confirma (accepted/duplicate); nunca se borra por fallar la red.
class Repository {
  Repository(this.db, {Uuid? uuid, DateTime Function()? clock})
      : _uuid = uuid ?? const Uuid(),
        _clock = clock ?? DateTime.now;

  final Database db;

  /// Vacas locales reemplazadas por la del servidor en el último merge (mismo arete).
  int relinked = 0;
  final Uuid _uuid;
  final DateTime Function() _clock;

  // ---- meta -------------------------------------------------------------
  Future<String?> getMeta(String key) async {
    final rows = await db.query('meta', where: 'key = ?', whereArgs: [key]);
    return rows.isEmpty ? null : rows.first['value'] as String?;
  }

  Future<void> setMeta(String key, String? value) async {
    if (value == null) {
      await db.delete('meta', where: 'key = ?', whereArgs: [key]);
    } else {
      await db.insert('meta', {'key': key, 'value': value},
          conflictAlgorithm: ConflictAlgorithm.replace);
    }
  }

  // ---- vacas ------------------------------------------------------------
  Future<Vaca> crearVaca({required String arete, String? nombre}) async {
    final cleanArete = arete.trim();
    if (cleanArete.isEmpty) throw ArgumentError('El arete es obligatorio');
    final cleanName = nombre?.trim();

    final vaca = Vaca(
      id: _uuid.v4(),
      arete: cleanArete,
      nombre: (cleanName == null || cleanName.isEmpty) ? null : cleanName,
      createdAt: _clock(),
    );
    try {
      await db.insert('vacas', vaca.toRow(), conflictAlgorithm: ConflictAlgorithm.abort);
    } on DatabaseException catch (e) {
      if (e.isUniqueConstraintError()) throw DuplicateAreteException(cleanArete);
      rethrow;
    }
    return vaca;
  }

  Future<List<VacaResumen>> vacas() async {
    final rows = await db.rawQuery('''
      SELECT v.*, m.nivel_riesgo AS ultimo_nivel, m.fecha_medicion AS ultima_fecha
      FROM vacas v
      LEFT JOIN mediciones m ON m.id = (
        SELECT id FROM mediciones WHERE vaca_id = v.id
        ORDER BY fecha_medicion DESC LIMIT 1)
      ORDER BY v.arete COLLATE NOCASE''');
    return rows.map((row) {
      final nivel = row['ultimo_nivel'] as String?;
      final fecha = row['ultima_fecha'] as String?;
      return VacaResumen(
        Vaca.fromRow(row),
        nivel == null ? null : RiskLevel.parse(nivel),
        fecha == null ? null : DateTime.parse(fecha),
      );
    }).toList();
  }

  Future<Vaca?> vaca(String id) async {
    final rows = await db.query('vacas', where: 'id = ?', whereArgs: [id]);
    return rows.isEmpty ? null : Vaca.fromRow(rows.first);
  }

  // ---- mediciones -------------------------------------------------------
  Future<Medicion> registrarMedicion({
    required String vacaId,
    required MedicionInput input,
    required LiteModel model,
  }) async {
    final record = <String, Object?>{
      'edad': input.edad,
      'raza': input.raza,
      'numero_de_partos': input.numeroDePartos,
      'volumen_de_leche': input.volumenDeLeche,
      'etapa_de_lactancia': input.etapaDeLactancia,
      'antecedentes_de_mastitis': input.antecedentesDeMastitis,
      'humedad': input.humedad,
      'temperatura': input.temperatura,
      'ph_leche': input.phLeche,
    };
    final errors = model.validate(record);
    if (errors.isNotEmpty) throw ArgumentError(errors.join('; '));

    final score = model.predict(record);
    final medicion = Medicion(
      id: _uuid.v4(),
      vacaId: vacaId,
      fecha: _clock(),
      edad: input.edad,
      raza: input.raza,
      numeroDePartos: input.numeroDePartos,
      volumenDeLeche: input.volumenDeLeche,
      etapaDeLactancia: input.etapaDeLactancia,
      antecedentesDeMastitis: input.antecedentesDeMastitis,
      humedad: input.humedad,
      temperatura: input.temperatura,
      phLeche: input.phLeche,
      probabilidad: score,
      nivelRiesgo: model.levelFor(score),
      modelVersion: model.version,
    );
    await db.insert('mediciones', medicion.toRow());
    return medicion;
  }

  Future<List<Medicion>> medicionesDe(String vacaId) async {
    final rows = await db.query('mediciones',
        where: 'vaca_id = ?', whereArgs: [vacaId], orderBy: 'fecha_medicion DESC');
    return rows.map(Medicion.fromRow).toList();
  }

  Future<Medicion?> medicion(String id) async {
    final rows = await db.query('mediciones', where: 'id = ?', whereArgs: [id]);
    return rows.isEmpty ? null : Medicion.fromRow(rows.first);
  }

  // ---- confirmaciones CMT ----------------------------------------------
  Future<Confirmacion> registrarConfirmacion({
    required String medicionId,
    required CmtGrade grado,
    String? evaluador,
    bool ciegoAlPh = false,
  }) async {
    final cleanEvaluator = evaluador?.trim();
    final confirmacion = Confirmacion(
      id: _uuid.v4(),
      medicionId: medicionId,
      fecha: _clock(),
      resultadoPositivo: grado.positive,
      grado: grado,
      evaluador: (cleanEvaluator == null || cleanEvaluator.isEmpty) ? null : cleanEvaluator,
      ciegoAlPh: ciegoAlPh,
    );
    await db.insert('confirmaciones', confirmacion.toRow());
    return confirmacion;
  }

  Future<Confirmacion?> confirmacionDe(String medicionId) async {
    final rows = await db.query('confirmaciones',
        where: 'medicion_id = ?', whereArgs: [medicionId], orderBy: 'fecha DESC', limit: 1);
    return rows.isEmpty ? null : Confirmacion.fromRow(rows.first);
  }

  // ---- sincronización ---------------------------------------------------
  Future<int> pendingCount() async {
    var total = 0;
    for (final kind in SyncKind.values) {
      total += Sqflite.firstIntValue(await db.rawQuery(
              "SELECT COUNT(*) FROM ${kind.table} WHERE sync_state = 'pending'")) ??
          0;
    }
    return total;
  }

  Future<int> rejectedCount() async {
    var total = 0;
    for (final kind in SyncKind.values) {
      total += Sqflite.firstIntValue(await db.rawQuery(
              "SELECT COUNT(*) FROM ${kind.table} WHERE sync_state = 'rejected'")) ??
          0;
    }
    return total;
  }

  /// Lote pendiente en orden de dependencia: vacas → mediciones → confirmaciones.
  Future<PendingBatch> pendingBatch({int limit = 200}) async {
    // Registros cuyo padre fue rechazado nunca podrán sincronizarse: se marcan.
    await db.rawUpdate('''
      UPDATE mediciones SET sync_state = 'rejected',
        sync_error = 'La vaca fue rechazada por el servidor'
      WHERE sync_state = 'pending'
        AND vaca_id IN (SELECT id FROM vacas WHERE sync_state = 'rejected')''');
    await db.rawUpdate('''
      UPDATE confirmaciones SET sync_state = 'rejected',
        sync_error = 'La medición fue rechazada por el servidor'
      WHERE sync_state = 'pending'
        AND medicion_id IN (SELECT id FROM mediciones WHERE sync_state = 'rejected')''');

    final vacas = await db.query('vacas',
        where: "sync_state = 'pending'", orderBy: 'created_at, rowid', limit: limit);
    var remaining = limit - vacas.length;
    final mediciones = remaining > 0
        ? await db.query('mediciones',
            where: "sync_state = 'pending'", orderBy: 'fecha_medicion, rowid', limit: remaining)
        : <Map<String, Object?>>[];
    remaining -= mediciones.length;
    final confirmaciones = remaining > 0
        ? await db.query('confirmaciones',
            where: "sync_state = 'pending'", orderBy: 'fecha, rowid', limit: remaining)
        : <Map<String, Object?>>[];

    return PendingBatch(
      vacas.map(Vaca.fromRow).toList(),
      mediciones.map(Medicion.fromRow).toList(),
      confirmaciones.map(Confirmacion.fromRow).toList(),
    );
  }

  /// Aplica los resultados del servidor. Devuelve cuántos cambiaron de estado
  /// (los `retry` no cambian nada y se reintentan en la siguiente sincronización).
  Future<int> applyResults(SyncKind kind, List<dynamic> results) async {
    var changed = 0;
    final batch = db.batch();
    for (final raw in results) {
      final result = raw as Map<String, dynamic>;
      final id = result['id'] as String?;
      if (id == null) continue;
      switch (result['status']) {
        case 'accepted':
        case 'duplicate':
          batch.update(kind.table, {'sync_state': 'synced', 'sync_error': null},
              where: 'id = ?', whereArgs: [id]);
          changed++;
        case 'rejected':
          batch.update(
              kind.table,
              {'sync_state': 'rejected', 'sync_error': (result['reason'] as String?) ?? 'Rechazado'},
              where: 'id = ?',
              whereArgs: [id]);
          changed++;
        default: // 'retry' u otro: sin cambios
          break;
      }
    }
    await batch.commit(noResult: true);
    return changed;
  }

  /// Inserta cambios del servidor sin tocar registros locales existentes.
  Future<int> mergeFromServer({
    List<dynamic> vacas = const [],
    List<dynamic> mediciones = const [],
    List<dynamic> confirmaciones = const [],
  }) async {
    var inserted = 0;
    relinked = 0;
    await db.transaction((txn) async {
      Future<void> put(String table, Map<String, Object?> row) async {
        final id = await txn.insert(table, {...row, 'sync_state': 'synced'},
            conflictAlgorithm: ConflictAlgorithm.ignore);
        if (id != 0) inserted++;
      }

      for (final raw in vacas) {
        final v = raw as Map<String, dynamic>;
        final serverId = v['id'] as String;
        if ((await txn.query('vacas', where: 'id = ?', whereArgs: [serverId], limit: 1))
            .isNotEmpty) {
          continue; // ya existe (propia o ya recibida)
        }

        // Otro teléfono creó el mismo arete con otro id: se adopta el id del
        // servidor y se reasignan las mediciones locales (que el servidor
        // había rechazado por "arete duplicado") para reenviarlas.
        final clash = await txn.query('vacas',
            where: 'arete = ? AND id != ?', whereArgs: [v['arete'], serverId], limit: 1);
        if (clash.isNotEmpty) {
          final localId = clash.first['id'] as String;
          await txn.delete('vacas', where: 'id = ?', whereArgs: [localId]);
          final moved = await txn.query('mediciones',
              columns: ['id'], where: 'vaca_id = ?', whereArgs: [localId]);
          await txn.update('mediciones', {'vaca_id': serverId},
              where: 'vaca_id = ?', whereArgs: [localId]);
          await txn.update('mediciones', {'sync_state': 'pending', 'sync_error': null},
              where: "vaca_id = ? AND sync_state = 'rejected' AND sync_error LIKE 'La vaca fue rechazada%'",
              whereArgs: [serverId]);
          for (final m in moved) {
            await txn.update('confirmaciones', {'sync_state': 'pending', 'sync_error': null},
                where: "medicion_id = ? AND sync_state = 'rejected' AND sync_error LIKE 'La medición fue rechazada%'",
                whereArgs: [m['id']]);
          }
          relinked++;
        }
        await put('vacas', {
          'id': v['id'],
          'arete': v['arete'],
          'nombre': v['nombre'],
          'created_at': _clock().toUtc().toIso8601String(),
        });
      }
      for (final raw in mediciones) {
        final m = raw as Map<String, dynamic>;
        await put('mediciones', {
          'id': m['id'],
          'vaca_id': m['vaca_id'],
          'fecha_medicion': m['fecha_medicion'],
          'edad': m['edad'],
          'raza': m['raza'],
          'numero_de_partos': m['numero_de_partos'],
          'volumen_de_leche': m['volumen_de_leche'],
          'etapa_de_lactancia': m['etapa_de_lactancia'],
          'antecedentes_de_mastitis': m['antecedentes_de_mastitis'],
          'humedad': m['humedad'],
          'temperatura': m['temperatura'],
          'ph_leche': m['ph_leche'],
          'probabilidad': m['probabilidad'],
          'nivel_riesgo': m['nivel_riesgo'],
          'model_version': m['model_version'],
        });
      }
      for (final raw in confirmaciones) {
        final c = raw as Map<String, dynamic>;
        await put('confirmaciones', {
          'id': c['id'],
          'medicion_id': c['medicion_id'],
          'fecha': c['fecha'],
          'resultado_positivo': (c['resultado_positivo'] as bool) ? 1 : 0,
          'grado': c['grado'],
          'evaluador': c['evaluador'],
          'ciego_al_ph': (c['ciego_al_ph'] as bool) ? 1 : 0,
        });
      }
    });
    return inserted;
  }
}
