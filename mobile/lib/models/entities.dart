import 'lite_model.dart';

enum SyncState {
  pending,
  synced,
  rejected;

  static SyncState parse(String? value) => SyncState.values.firstWhere(
        (s) => s.name == value,
        orElse: () => SyncState.pending,
      );
}

class Vaca {
  const Vaca({
    required this.id,
    required this.arete,
    this.nombre,
    required this.createdAt,
    this.syncState = SyncState.pending,
    this.syncError,
  });

  final String id;
  final String arete;
  final String? nombre;
  final DateTime createdAt;
  final SyncState syncState;
  final String? syncError;

  String get titulo => (nombre == null || nombre!.isEmpty) ? arete : '$arete · $nombre';

  Map<String, Object?> toRow() => {
        'id': id,
        'arete': arete,
        'nombre': nombre,
        'created_at': createdAt.toUtc().toIso8601String(),
        'sync_state': syncState.name,
        'sync_error': syncError,
      };

  factory Vaca.fromRow(Map<String, Object?> row) => Vaca(
        id: row['id'] as String,
        arete: row['arete'] as String,
        nombre: row['nombre'] as String?,
        createdAt: DateTime.parse(row['created_at'] as String),
        syncState: SyncState.parse(row['sync_state'] as String?),
        syncError: row['sync_error'] as String?,
      );

  Map<String, Object?> toApi() => {'id': id, 'arete': arete, 'nombre': nombre};
}

class Medicion {
  const Medicion({
    required this.id,
    required this.vacaId,
    required this.fecha,
    required this.edad,
    required this.raza,
    required this.numeroDePartos,
    this.volumenDeLeche,
    required this.etapaDeLactancia,
    required this.antecedentesDeMastitis,
    this.humedad,
    this.temperatura,
    required this.phLeche,
    required this.probabilidad,
    required this.nivelRiesgo,
    required this.modelVersion,
    this.syncState = SyncState.pending,
    this.syncError,
  });

  final String id;
  final String vacaId;
  final DateTime fecha;
  final int edad;
  final String raza;
  final int numeroDePartos;
  final double? volumenDeLeche;
  final int etapaDeLactancia; // 0 temprana, 1 tardía
  final int antecedentesDeMastitis; // 0 no, 1 sí
  final double? humedad;
  final double? temperatura;
  final double phLeche;
  final double probabilidad; // puntaje del modelo, no calibrado
  final RiskLevel nivelRiesgo;
  final String modelVersion;
  final SyncState syncState;
  final String? syncError;

  Map<String, Object?> toRow() => {
        'id': id,
        'vaca_id': vacaId,
        'fecha_medicion': fecha.toUtc().toIso8601String(),
        'edad': edad,
        'raza': raza,
        'numero_de_partos': numeroDePartos,
        'volumen_de_leche': volumenDeLeche,
        'etapa_de_lactancia': etapaDeLactancia,
        'antecedentes_de_mastitis': antecedentesDeMastitis,
        'humedad': humedad,
        'temperatura': temperatura,
        'ph_leche': phLeche,
        'probabilidad': probabilidad,
        'nivel_riesgo': nivelRiesgo.name,
        'model_version': modelVersion,
        'sync_state': syncState.name,
        'sync_error': syncError,
      };

  factory Medicion.fromRow(Map<String, Object?> row) => Medicion(
        id: row['id'] as String,
        vacaId: row['vaca_id'] as String,
        fecha: DateTime.parse(row['fecha_medicion'] as String),
        edad: row['edad'] as int,
        raza: row['raza'] as String,
        numeroDePartos: row['numero_de_partos'] as int,
        volumenDeLeche: (row['volumen_de_leche'] as num?)?.toDouble(),
        etapaDeLactancia: row['etapa_de_lactancia'] as int,
        antecedentesDeMastitis: row['antecedentes_de_mastitis'] as int,
        humedad: (row['humedad'] as num?)?.toDouble(),
        temperatura: (row['temperatura'] as num?)?.toDouble(),
        phLeche: (row['ph_leche'] as num).toDouble(),
        probabilidad: (row['probabilidad'] as num).toDouble(),
        nivelRiesgo: RiskLevel.parse(row['nivel_riesgo'] as String),
        modelVersion: row['model_version'] as String,
        syncState: SyncState.parse(row['sync_state'] as String?),
        syncError: row['sync_error'] as String?,
      );

  /// Variables de entrada del modelo (mismos nombres que el dataset).
  Map<String, Object?> get inputs => {
        'edad': edad,
        'raza': raza,
        'numero_de_partos': numeroDePartos,
        'volumen_de_leche': volumenDeLeche,
        'etapa_de_lactancia': etapaDeLactancia,
        'antecedentes_de_mastitis': antecedentesDeMastitis,
        'humedad': humedad,
        'temperatura': temperatura,
        'ph_leche': phLeche,
      };

  Map<String, Object?> toApi() => {
        'id': id,
        'vaca_id': vacaId,
        'fecha_medicion': fecha.toUtc().toIso8601String(),
        ...inputs,
        'probabilidad': probabilidad,
        'nivel_riesgo': nivelRiesgo.name,
        'model_version': modelVersion,
      };
}

/// Escala CMT: N y T son negativos; 1, 2 y 3 son positivos.
enum CmtGrade {
  n('N', 'Negativo', false),
  t('T', 'Trazas', false),
  uno('1', '+ (1)', true),
  dos('2', '++ (2)', true),
  tres('3', '+++ (3)', true);

  const CmtGrade(this.code, this.label, this.positive);
  final String code;
  final String label;
  final bool positive;

  static CmtGrade? parse(String? code) {
    for (final g in CmtGrade.values) {
      if (g.code == code) return g;
    }
    return null;
  }
}

class Confirmacion {
  const Confirmacion({
    required this.id,
    required this.medicionId,
    required this.fecha,
    required this.resultadoPositivo,
    this.grado,
    this.evaluador,
    this.ciegoAlPh = false,
    this.syncState = SyncState.pending,
    this.syncError,
  });

  final String id;
  final String medicionId;
  final DateTime fecha;
  final bool resultadoPositivo;
  final CmtGrade? grado;
  final String? evaluador;
  final bool ciegoAlPh;
  final SyncState syncState;
  final String? syncError;

  Map<String, Object?> toRow() => {
        'id': id,
        'medicion_id': medicionId,
        'fecha': fecha.toUtc().toIso8601String(),
        'resultado_positivo': resultadoPositivo ? 1 : 0,
        'grado': grado?.code,
        'evaluador': evaluador,
        'ciego_al_ph': ciegoAlPh ? 1 : 0,
        'sync_state': syncState.name,
        'sync_error': syncError,
      };

  factory Confirmacion.fromRow(Map<String, Object?> row) => Confirmacion(
        id: row['id'] as String,
        medicionId: row['medicion_id'] as String,
        fecha: DateTime.parse(row['fecha'] as String),
        resultadoPositivo: (row['resultado_positivo'] as int) == 1,
        grado: CmtGrade.parse(row['grado'] as String?),
        evaluador: row['evaluador'] as String?,
        ciegoAlPh: (row['ciego_al_ph'] as int) == 1,
        syncState: SyncState.parse(row['sync_state'] as String?),
        syncError: row['sync_error'] as String?,
      );

  Map<String, Object?> toApi() => {
        'id': id,
        'medicion_id': medicionId,
        'fecha': fecha.toUtc().toIso8601String(),
        'resultado_positivo': resultadoPositivo,
        'grado': grado?.code,
        'evaluador': evaluador,
        'ciego_al_ph': ciegoAlPh,
      };
}

/// Entradas de formulario para registrar una medición.
class MedicionInput {
  const MedicionInput({
    required this.edad,
    required this.raza,
    required this.numeroDePartos,
    this.volumenDeLeche,
    required this.etapaDeLactancia,
    required this.antecedentesDeMastitis,
    this.humedad,
    this.temperatura,
    required this.phLeche,
  });

  final int edad;
  final String raza;
  final int numeroDePartos;
  final double? volumenDeLeche;
  final int etapaDeLactancia;
  final int antecedentesDeMastitis;
  final double? humedad;
  final double? temperatura;
  final double phLeche;
}
