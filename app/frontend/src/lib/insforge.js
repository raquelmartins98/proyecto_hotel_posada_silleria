/**
 * Cliente Insforge — API REST estándar con Anon Key (JWT anónimo)
 * Hotel Boutique Posada de la Sillería (Toledo)
 *
 * Usa GET /api/database/records/{tabla} para lecturas públicas.
 * Autenticación vía Authorization: Bearer <anon-key>.
 *
 * NO usa /api/database/advance/rawsql (requiere clave de servicio ik_).
 *
 * Funciones exportadas:
 *   select(table, options)   → Lectura REST directa (NUEVO CÓDIGO)
 *   create(table, records)   → Inserción REST directa (NUEVO CÓDIGO)
 *   update(table, id, data)  → Actualización PATCH por ID (NUEVO CÓDIGO)
 *   remove(table, id)        → Eliminación DELETE por ID (NUEVO CÓDIGO)
 *   query(sql, params)       → Puente SELECT SQL → REST (para hooks legacy)
 *   mutate(sql, params)      → Puente INSERT SQL → REST (para hooks legacy)
 *   healthCheck()            → Verifica conexión con la API
 *
 * Uso nuevo código:
 *   import { select } from "../lib/insforge";
 *   const habitaciones = await select("habitaciones", { order: "tarifa_base.asc" });
 *
 * Uso hooks legacy (query/mutate convierten SQL a REST automáticamente):
 *   import { useInsforgeQuery } from "../hooks/useInsforge";
 *   const { data } = useInsforgeQuery("SELECT * FROM public.habitaciones ORDER BY tarifa_base");
 */

// ── Config: VITE env vars con fallback ──
const API_BASE_URL =
  import.meta.env.VITE_INSFORGE_URL || "https://v63axieg.us-east.insforge.app";

const ANON_KEY = import.meta.env.VITE_INSFORGE_ANON_KEY || "";

// ── Headers de autenticación ──
function getAuthHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (ANON_KEY) {
    headers["Authorization"] = `Bearer ${ANON_KEY}`;
  }
  return headers;
}

// ── Parseador de SELECT SQL para el puente query() ──
// Patrones soportados:
//   SELECT columns FROM [public.]table [ORDER BY col [ASC|DESC], ...] [LIMIT N]
const SELECT_RE = /^\s*SELECT\s+(.+?)\s+FROM\s+(?:public\.)?(\w+)(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?\s*$/i;

/**
 * Convierte una sentencia SELECT SQL en opciones para select().
 * Lanza error si el SQL no sigue el patrón esperado.
 */
function parseSelectSQL(sql) {
  const match = sql.match(SELECT_RE);
  if (!match) {
    throw new Error(
      `query(): SQL no reconocido. Usa formato: SELECT cols FROM public.tabla [ORDER BY col [ASC|DESC]] [LIMIT N]. ` +
      `Para consultas complejas usa select() directamente.`
    );
  }

  const [, columns, table, orderClause, limitStr] = match;

  const options = {};

  // Columnas: "col1, col2, col3" o "*"
  const cols = columns.trim();
  if (cols !== "*") {
    options.select = cols;
  }

  // ORDER BY: "col1 ASC, col2 DESC" → "col1.asc, col2.desc"
  if (orderClause) {
    const parts = orderClause.trim().split(/\s*,\s*/);
    const orderParts = parts.map((part) => {
      const [col, dir] = part.trim().split(/\s+/);
      const direction = dir?.toLowerCase() === "desc" ? "desc" : "asc";
      // Saltar direcciones duplicadas estilo "col.asc.asc"
      return col.includes(".") ? col : `${col}.${direction}`;
    });
    options.order = orderParts.join(",");
  }

  // LIMIT
  if (limitStr) {
    options.limit = parseInt(limitStr, 10);
  } else {
    options.limit = 100; // Valor por defecto seguro
  }

  return { table, options };
}

// ── Parseador de INSERT SQL para el puente mutate() ──
// Patrón soportado:
//   INSERT INTO [public.]table (col1, col2, ...) VALUES ($1, $2::type?, ...)
const INSERT_RE = /^\s*INSERT\s+INTO\s+(?:public\.)?(\w+)\s*\(([^)]+)\)\s*VALUES\s*\((.+?)\)\s*$/i;

/**
 * Convierte una sentencia INSERT SQL + params en { table, records } para create().
 * Lanza error si el SQL no sigue el patrón esperado.
 */
function parseInsertSQL(sql, params) {
  const match = sql.match(INSERT_RE);
  if (!match) {
    throw new Error(
      `mutate(): SQL no reconocido. Usa formato: INSERT INTO public.tabla (col1, col2) VALUES ($1, $2). ` +
      `Para operaciones complejas usa create() directamente.`
    );
  }

  const [, table, columnsStr, placeholdersStr] = match;

  // Extraer nombres de columnas
  const columns = columnsStr.split(",").map((c) => c.trim());

  // Extraer placeholders: $1, $2, $3::date, etc.
  const placeholders = placeholdersStr.split(",").map((p) => p.trim());

  // Mapear params a columnas según el número de placeholder ($1 → params[0], etc.)
  const record = {};
  placeholders.forEach((ph, i) => {
    const matchPh = ph.match(/^\$(\d+)/);
    if (matchPh) {
      const paramIdx = parseInt(matchPh[1], 10) - 1;
      if (paramIdx >= 0 && paramIdx < params.length) {
        record[columns[i]] = params[paramIdx];
      }
    }
  });

  return { table, records: record };
}

// ════════════════════════════════════════════════════════════════
//  API PÚBLICA — Funciones principales
// ════════════════════════════════════════════════════════════════

/**
 * SELECT — Consulta registros de una tabla via REST.
 *
 * @param {string} table - Nombre de la tabla (ej: "habitaciones", "reservas")
 * @param {object} [options]
 * @param {string} [options.select] - Columnas separadas por coma (ej: "id,tipo,tarifa_base")
 * @param {string} [options.order] - Orden (ej: "fecha_entrada.desc", "tarifa_base.asc")
 * @param {number} [options.limit=100] - Máximo de registros (1-1000)
 * @param {number} [options.offset=0] - Desplazamiento para paginación
 * @param {object} [options.filters] - Filtros tipo PostgREST (ej: { "status": "eq.published" })
 * @returns {Promise<object[]>} - Array de registros
 */
export async function select(table, options = {}) {
  const {
    select: columns,
    order,
    limit = 100,
    offset = 0,
    filters = {},
  } = options;

  const params = new URLSearchParams();

  if (columns) params.set("select", columns);
  if (limit) params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));
  if (order) params.set("order", order);

  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null) {
      params.set(key, value);
    }
  }

  const qs = params.toString();
  const url = `${API_BASE_URL}/api/database/records/${table}${qs ? `?${qs}` : ""}`;

  const response = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error");
    throw new Error(`Insforge select failed (${response.status}): ${text}`);
  }

  const json = await response.json();

  // La API Insforge devuelve dos formatos según la query:
  //   con "select=col1,col2" → array plano [...]
  //   sin "select="          → { value: [...], Count: N }
  // Normalizamos siempre a array plano.
  if (json && typeof json === "object" && Array.isArray(json.value)) {
    return json.value;
  }

  return Array.isArray(json) ? json : [];
}

/**
 * CREATE — Inserta uno o varios registros en una tabla.
 * NOTA: Requiere que el rol anónimo tenga permiso de INSERT o
 * que el usuario esté autenticado.
 *
 * @param {string} table - Nombre de la tabla
 * @param {object|object[]} records - Objeto o array de objetos a insertar
 * @returns {Promise<object[]>} - Registros creados
 */
export async function create(table, records) {
  const body = Array.isArray(records) ? records : [records];

  const response = await fetch(
    `${API_BASE_URL}/api/database/records/${table}`,
    {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        Prefer: "return=representation",
      },
      body: JSON.stringify(body),
    }
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error");
    throw new Error(`Insforge create failed (${response.status}): ${text}`);
  }

  return response.json();
}

/**
 * UPDATE — Actualiza un registro existente por ID vía PATCH REST.
 *
 * @param {string} table - Nombre de la tabla
 * @param {string} id - UUID del registro a actualizar
 * @param {object} record - Objeto con los campos a modificar
 * @returns {Promise<object[]>} - Registro(s) actualizado(s)
 */
export async function update(table, id, record) {
  const response = await fetch(
    `${API_BASE_URL}/api/database/records/${table}?id=eq.${id}`,
    {
      method: "PATCH",
      headers: {
        ...getAuthHeaders(),
        Prefer: "return=representation",
      },
      body: JSON.stringify(record),
    }
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error");
    throw new Error(`Insforge update failed (${response.status}): ${text}`);
  }

  return response.json();
}

/**
 * REMOVE — Elimina un registro por ID vía DELETE REST.
 *
 * @param {string} table - Nombre de la tabla
 * @param {string} id - UUID del registro a eliminar
 * @returns {Promise<void>}
 */
export async function remove(table, id) {
  const response = await fetch(
    `${API_BASE_URL}/api/database/records/${table}?id=eq.${id}`,
    { method: "DELETE", headers: getAuthHeaders() }
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error");
    throw new Error(`Insforge remove failed (${response.status}): ${text}`);
  }
}

// ════════════════════════════════════════════════════════════════
//  PUENTE LEGACY — query() / mutate()
//  Parsea SQL simple y lo traduce a llamadas REST.
//  Existen para mantener compatibilidad con hooks y páginas
//  existentes. El código NUEVO debe usar select() / create().
// ════════════════════════════════════════════════════════════════

/**
 * query — Ejecuta una consulta SELECT usando SQL simplificado.
 *
 * Internamente parsea el SQL y llama a select() con REST.
 * Soporta:
 *   SELECT cols FROM [public.]tabla [ORDER BY col [ASC|DESC]] [LIMIT N]
 *
 * @param {string} sql - Sentencia SELECT SQL
 * @param {any[]} [_params] - NO usado en SELECT (se ignora)
 * @returns {Promise<object[]>} - Array de registros
 */
export async function query(sql, _params = []) {
  const { table, options } = parseSelectSQL(sql);
  return select(table, options);
}

/**
 * mutate — Ejecuta una sentencia INSERT usando SQL simplificado.
 *
 * Internamente parsea el SQL y los placeholders ($1, $2, ...)
 * y llama al endpoint REST POST.
 * Soporta:
 *   INSERT INTO [public.]tabla (col1, col2) VALUES ($1, $2::type?)
 *
 * @param {string} sql - Sentencia INSERT SQL
 * @param {any[]} params - Valores para los placeholders ($1, $2, ...)
 * @returns {Promise<object[]>} - Registros creados
 */
export async function mutate(sql, params = []) {
  const { table, records } = parseInsertSQL(sql, params);
  return create(table, records);
}

/**
 * healthCheck — Verifica el estado de la API Insforge.
 * @returns {Promise<{ok: boolean, status: string}>}
 */
export async function healthCheck() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) return { ok: true, status: "connected" };
    return { ok: false, status: `HTTP ${response.status}` };
  } catch (err) {
    return { ok: false, status: err.message };
  }
}

export { API_BASE_URL };
