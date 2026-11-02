import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// Apertura y esquema de la base SQLite local (fuente de verdad offline).
///
/// No se declaran claves foráneas: durante el pull, las filas pueden llegar en
/// páginas distintas (p. ej. una medición antes que su vaca) y la integridad
/// se garantiza a nivel de aplicación.
class AppDatabase {
  static const schemaVersion = 1;

  /// [path] = `inMemoryDatabasePath` en pruebas.
  static Future<Database> open({String? path}) async {
    final resolved = path ?? p.join(await getDatabasesPath(), 'mastitis.db');
    return openDatabase(
      resolved,
      version: schemaVersion,
      onCreate: _create,
      // Las bases en memoria no deben compartirse entre aperturas (pruebas).
      singleInstance: resolved != inMemoryDatabasePath,
    );
  }

  static Future<void> _create(Database db, int version) async {
    await db.execute('''
      CREATE TABLE vacas (
        id TEXT PRIMARY KEY,
        arete TEXT NOT NULL UNIQUE,
        nombre TEXT,
        created_at TEXT NOT NULL,
        sync_state TEXT NOT NULL DEFAULT 'pending',
        sync_error TEXT
      )''');
    await db.execute('''
      CREATE TABLE mediciones (
        id TEXT PRIMARY KEY,
        vaca_id TEXT NOT NULL,
        fecha_medicion TEXT NOT NULL,
        edad INTEGER NOT NULL,
        raza TEXT NOT NULL,
        numero_de_partos INTEGER NOT NULL,
        volumen_de_leche REAL,
        etapa_de_lactancia INTEGER NOT NULL,
        antecedentes_de_mastitis INTEGER NOT NULL,
        humedad REAL,
        temperatura REAL,
        ph_leche REAL NOT NULL,
        probabilidad REAL NOT NULL,
        nivel_riesgo TEXT NOT NULL,
        model_version TEXT NOT NULL,
        sync_state TEXT NOT NULL DEFAULT 'pending',
        sync_error TEXT
      )''');
    await db.execute('CREATE INDEX idx_med_vaca ON mediciones(vaca_id, fecha_medicion)');
    await db.execute('''
      CREATE TABLE confirmaciones (
        id TEXT PRIMARY KEY,
        medicion_id TEXT NOT NULL,
        fecha TEXT NOT NULL,
        resultado_positivo INTEGER NOT NULL,
        grado TEXT,
        evaluador TEXT,
        ciego_al_ph INTEGER NOT NULL DEFAULT 0,
        sync_state TEXT NOT NULL DEFAULT 'pending',
        sync_error TEXT
      )''');
    await db.execute('CREATE INDEX idx_conf_med ON confirmaciones(medicion_id)');
    await db.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)');
  }
}
