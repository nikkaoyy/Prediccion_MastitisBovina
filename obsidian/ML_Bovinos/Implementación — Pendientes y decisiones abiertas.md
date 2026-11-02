# Implementación — Pendientes y decisiones abiertas

Parte de [[Implementación 2026-11-01 — Índice]].

## Decisiones de los autores
- [ ] ¿Se mantienen las 9 variables del Modelo B o se simplifica a solo pH? (El modelo solo-pH iguala o supera al B; ver [[Implementación — Hallazgos de la revisión]].)
- [ ] Definir la verdad de referencia del CMT: quién lo lee, cuándo, escala, ciego al pH (ver `docs/protocolo_verdad_referencia.md`).
- [ ] Umbrales: CV anidada o esperar datos nuevos.
- [ ] Aplicar `docs/cambios_articulo.md` al .docx (no se modificó).
- [ ] Aclarar roles de autoría y estado de aprobación del CIDC.
- [ ] Estado del derecho de petición ante ICA y FEDEGÁN.

## Técnico
- [ ] Modo ciego en la app.
- [ ] Probar en dispositivo Android físico.
- [ ] Token en almacén seguro del sistema.
- [ ] Cursor de pull en PostgreSQL y pruebas contra Postgres.
- [ ] Edición y borrado de registros; resolución de conflictos de edición.
- [ ] Gestión de usuarios y roles.
- [ ] Reentrenamiento: hoy es manual con `export_model`.
- [ ] Commits: hay cambios sin commitear (repositorio y `docs/`, `server/`, `mobile/`, `models/`).

## Datos
- [ ] Recolectar datos nuevos con el protocolo (fincas nuevas, lectura ciega, todas las vacas con CMT).
- [ ] Notas antiguas de Obsidian con "208 filas" o "7 registros": corregir a 209 y 8 nulos.
