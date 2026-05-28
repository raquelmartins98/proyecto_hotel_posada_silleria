# Sistema de Diseño — Posada Sillería Admin Dashboard

> **Fuente:** Proyecto Stitch "Posada Sillería Admin Dashboard" (`projects/13571982919460806086`)
> **Tema:** Heritage Ledger — "Sober Editorial" con herencia toledana
> **Fecha de extracción:** 2026-05-19

---

## 1. Filosofía de diseño

Fusión sofisticada de la **herencia toledana** con la utilidad de un SaaS de alto rendimiento. Diseñado para el hotelero moderno que valora precisión, historia y "lujo silencioso".

- **Estilo:** "Sober Editorial" — generosos espacios en blanco, bordes finos, tensión equilibrada entre tipografía serif (narrativa/marca) y sans-serif funcional (datos).
- **Sensación:** Confiabilidad y prestigio. Herramienta artesanal: cara, bien construida, esencial.
- **Evita:** La esterilidad fría del software empresarial típico.

---

## 2. Paleta de colores

### 2.1 Colores semánticos (overrides — la intención real del diseño)

| Token | Hex | Uso semántico |
|-------|-----|---------------|
| `--color-primary` | **#b8860b** | Gold — acciones de alta intención, botones primarios, indicadores de estado crítico |
| `--color-secondary` | **#3e2c1c** | Dark Brown — texto principal, navegación, sidebar background |
| `--color-tertiary` | **#8a7e6d** | Warm Grey — texto secundario, metadatos, iconos de soporte |
| `--color-neutral` | **#f5efe6** | Cream — fondo principal, calidad "papel" que reduce fatiga visual |

### 2.2 Paleta completa (Material Design 3 — namedColors)

#### Superficies y fondos

| Token | Hex | Uso |
|-------|-----|-----|
| `background` / `surface` / `surface-bright` | **#fff9ef** | Fondo general de la app |
| `surface-dim` | **#dfd9d1** | Superficie atenuada (modales, drawers) |
| `surface-container-lowest` | **#ffffff** | Blanco puro — tarjetas, inputs |
| `surface-container-low` | **#f9f3ea** | Contenedores de baja elevación |
| `surface-container` | **#f3ede4** | Contenedores base |
| `surface-container-high` | **#ede7de** | Barra de herramientas, headers de tabla |
| `surface-container-highest` | **#e7e2d9** | Elementos elevados |
| `surface-variant` | **#e7e2d9** | Variante de superficie |

#### Texto e iconos

| Token | Hex | Uso |
|-------|-----|-----|
| `on-surface` / `on-background` | **#1d1b16** | Texto principal (casi negro, ligeramente cálido) |
| `on-surface-variant` | **#4f4535** | Texto secundario, subtítulos, placeholders |
| `inverse-on-surface` | **#f6f0e7** | Texto sobre fondo oscuro (inversa) |

#### Primario (Gold)

| Token | Hex | Uso |
|-------|-----|-----|
| `primary` | **#785600** | Gold oscuro — badges, acentos |
| `on-primary` | **#ffffff** | Texto sobre primary |
| `primary-container` | **#986d00** | Gold medio — hover states |
| `on-primary-container` | **#fffbff** | Texto sobre primary-container |
| `primary-fixed` | **#ffdea6** | Gold claro — fondos de acento |
| `primary-fixed-dim` | **#f7bd48** | Gold brillante — inverse-primary |
| `inverse-primary` | **#f7bd48** | Primary en modo oscuro |
| `surface-tint` | **#7b5800** | Tinte de superficie |
| `on-primary-fixed` | **#271900** | Texto sobre primary-fixed |
| `on-primary-fixed-variant` | **#5d4200** | Variante texto primary |

#### Secundario (Dark Brown / Warm)

| Token | Hex | Uso |
|-------|-----|-----|
| `secondary` | **#705a47** | Marrón medio — badges secundarios |
| `on-secondary` | **#ffffff** | Texto sobre secondary |
| `secondary-container` | **#fcddc5** | Fondo cálido claro |
| `secondary-fixed` | **#fcddc5** | Fijo secundario |
| `secondary-fixed-dim` | **#dec1aa** | Atenuado |
| `on-secondary-container` | **#77604d** | Texto sobre secondary-container |
| `on-secondary-fixed` | **#28180a** | Texto secondary-fixed |
| `on-secondary-fixed-variant` | **#574331** | Variante texto secondary |

#### Terciario (Warm Grey)

| Token | Hex | Uso |
|-------|-----|-----|
| `tertiary` | **#655a4b** | Gris cálido — metadatos |
| `on-tertiary` | **#ffffff** | Texto sobre tertiary |
| `tertiary-container` | **#7e7362** | Gris medio |
| `tertiary-fixed` | **#f0e0cc** | Fondo terciario claro |
| `tertiary-fixed-dim` | **#d3c4b1** | Atenuado terciario |

#### Error / Alerta / Éxito

| Token | Hex | Uso |
|-------|-----|-----|
| `error` | **#ba1a1a** | Rojo — errores, diferencias negativas de precio |
| `on-error` | **#ffffff** | Texto sobre error |
| `error-container` | **#ffdad6** | Fondo de error claro |
| `on-error-container` | **#93000a** | Texto error-container |
| *Éxito (verde)* | **#2e7d32** | Diferencias positivas de precio (usado en tablas) |
| *Éxito claro* | **#e8f5e9** | Fondo de éxito (inferido) |

#### Bordes y estructura

| Token | Hex | Uso |
|-------|-----|-----|
| `outline` | **#817563** | Bordes primarios |
| `outline-variant` | **#d3c4af** | Bordes secundarios, separadores, líneas de tabla |
| `inverse-surface` | **#32302a** | Superficie inversa (dark mode) |

---

## 3. Tipografía

### 3.1 Familias

| Rol | Fuente | Uso |
|-----|--------|-----|
| **Serif (cabeceras)** | **Playfair Display** | Títulos de página, encabezados de sección, resúmenes de alto nivel. Evoca raíces históricas |
| **Sans (funcional)** | **Inter** | UI funcional, tablas de datos, campos de formulario, cuerpo. Legibilidad a tamaños pequeños |
| **Data Display** | **Inter** (monoespaciado numérico) | Datos tabulares y precios — alineación vertical en reportes |

### 3.2 Escala tipográfica

| Token | Font Family | Size | Weight | Line Height | Letter Spacing | Uso |
|-------|-------------|------|--------|-------------|----------------|-----|
| `display-lg` | Playfair Display | **48px** | **700** | 1.2 | **-0.02em** | Hero, grandes títulos de landing |
| `headline-lg` | Playfair Display | **32px** | **600** | 1.3 | normal | Títulos de página (dashboard) |
| `headline-lg-mobile` | Playfair Display | **28px** | **600** | 1.3 | normal | Títulos en móvil |
| `headline-md` | Playfair Display | **24px** | **600** | 1.4 | normal | Subtítulos, encabezados de sección |
| `body-lg` | Inter | **18px** | **400** | 1.6 | normal | Cuerpo grande, descripciones |
| `body-md` | Inter | **16px** | **400** | 1.5 | normal | Cuerpo base, párrafos |
| `label-md` | Inter | **14px** | **500** | 1.0 | **0.05em** | Labels de campo, navegación, uppercase |
| `data-tabular` | Inter | **13px** | **400** | 1.0 | normal | Celdas de tabla, datos numéricos |

### 3.3 Reglas tipográficas

| Elemento | Aplicación |
|----------|------------|
| Labels de formulario | `label-md` en **uppercase**, posicionados **encima** del campo |
| Navegación sidebar | `label-md` con iconos |
| Datos en tabla | `data-tabular` (alineación vertical de números) |
| Headers de tabla | `label-md` en uppercase con color `on-surface-variant` |

---

## 4. Espaciado

### 4.1 Escala de spacing

| Token | Valor | Uso típico |
|-------|-------|------------|
| `xs` | **4px** (0.25rem) | Micro-espaciado, gap entre icono y texto pequeño |
| `base` | **8px** (0.5rem) | **Múltiplo base** — rejilla vertical, padding de sidebar |
| `sm` | **12px** (0.75rem) | Padding de barras de filtro, gap compacto |
| `md` | **24px** (1.5rem) | Padding de tarjetas, gap de grid, padding de main |
| `lg` | **48px** (3rem) | Separación entre secciones mayores |
| `xl` | **80px** (5rem) | Espaciado generoso, hero sections |
| `gutter` | **24px** (1.5rem) | Gap del grid bento (12 columnas) |
| `margin-mobile` | **16px** (1rem) | Márgenes laterales en móvil |
| `margin-desktop` | **40px** (2.5rem) | Márgenes laterales en desktop |

### 4.2 Rejilla (Grid)

| Propiedad | Valor |
|-----------|-------|
| Sistema | **Fixed-Fluid Hybrid** |
| Columnas | **12** (fluid grid, clase `.bento-grid`) |
| Gap | `gutter`: **24px** |
| Breakpoints | Desktop (1440px+): 12 cols, 40px margins |
| | Tablet (768-1439px): 8 cols, 24px margins |
| | Mobile (0-767px): 4 cols, 16px margins |
| Vertical rhythm | Baseline grid de **8px** estricto |

### 4.3 Elevación y sombras

| Elemento | Sombra |
|----------|--------|
| Hover de elementos interactivos | `0px 4px 12px rgba(62, 44, 28, 0.05)` — sombra ambiental muy sutil |
| Tarjetas | **Sin sombra** — solo borde de 1px `#DED7CD` |
| Sidebar | Fija, sin sombra |

> **Regla:** Sin sombras pesadas. La profundidad se comunica mediante **bordes de bajo contraste** y **capas tonales** (surface-container-low → highest).

---

## 5. Bordes y radios

### 5.1 Escala de border-radius

| Token | Valor | Uso |
|-------|-------|-----|
| `sm` | **0.125rem** (2px) | Micro-interactivos |
| `DEFAULT` | **0.25rem** (4px) | **Radio principal** — botones, inputs, tarjetas |
| `md` | **0.375rem** (6px) | No se usa en el diseño actual |
| `lg` | **0.5rem** (8px) | Componentes mayores |
| `xl` | **0.75rem** (12px) | No se usa en el diseño actual |
| `full` | **9999px** | Avatares, badges circulares |

### 5.2 Reglas de bordes

| Elemento | Borde |
|----------|-------|
| Tarjetas | 1px sólido `outline-variant` (#D3C4AF) |
| Inputs | 1px sólido `outline-variant` (#D3C4AF), focus → `primary` |
| Sidebar | `border-r border-outline-variant` |
| Tabla | `border-collapse`, separadores horizontales `divide-y divide-outline-variant/30` |
| Separadores verticales | 1px `outline-variant`, 8px height |

---

## 6. Componentes

### 6.1 Botones

| Estado | Clase | Fondo | Texto | Borde | Hover |
|--------|-------|-------|-------|-------|-------|
| **Primario** | `bg-primary text-on-primary` | `#b8860b` (Gold) | `#ffffff` | Ninguno | `brightness-110` + `scale-95` |
| **Secundario (outline)** | `border border-on-surface text-on-surface` | Transparente | `#1d1b16` | 1px `on-surface` | `bg-on-surface text-surface` |
| **Terciario (text)** | `text-on-surface hover:bg-surface-container-high` | Transparente | `#1d1b16` | Ninguno | `bg-surface-container-high` |
| **Icono** | `hover:bg-surface-container-high p-2` | Transparente | — | Ninguno | `bg-surface-container-high` |
| **Deshabilitado** | `disabled:opacity-30` | — | — | — | `opacity-30` |

**Transiciones comunes:** `transition-colors active:scale-95`

| Botón | Padding | Font |
|-------|---------|------|
| Primario grande | `px-8 py-3` | `font-label-md uppercase tracking-widest` |
| Primario estándar | `px-6 py-3` | `font-label-md uppercase tracking-widest` |
| Secundario outline | `py-3` (full width) | `font-label-md uppercase tracking-widest` |
| Icono + texto | `px-3 py-2` | `font-label-md` |

### 6.2 Inputs

| Elemento | Clase | Estilo |
|----------|-------|--------|
| Input de búsqueda | `w-full pl-10 pr-4 py-2 bg-surface-container border border-outline-variant focus:outline-none focus:border-primary transition-colors font-body-md` | Fondo `surface-container`, borde `outline-variant`, focus → `primary` |
| Selector dropdown | `flex items-center gap-3 bg-white px-4 py-2 border border-outline-variant` | Blanco, label en `text-[10px] uppercase font-bold`, valor en `font-label-md` |
| Label | `text-[10px] text-on-surface-variant uppercase font-bold` | Micro-label encima del valor |

### 6.3 Tarjetas (Cards)

| Propiedad | Valor |
|-----------|-------|
| Background | `bg-surface-container-lowest` (#ffffff) |
| Border | `border border-outline-variant` (#D3C4AF) |
| Shadow | **Ninguno** por defecto |
| Padding | `p-md` (24px) |
| Hover | `hover:bg-surface-container-low transition-colors duration-300` (solo en cards interactivas) |

### 6.4 Tablas de datos

| Elemento | Clase / Estilo |
|----------|----------------|
| Contenedor | `overflow-hidden bg-surface-container-lowest border border-outline-variant` |
| Overflow | `overflow-x-auto` |
| Estructura | `w-full text-left border-collapse` |
| Header row | `bg-surface-container-high/50 border-b border-outline-variant` |
| Header cell | `px-6 py-4 font-label-md text-on-surface-variant uppercase tracking-wider` |
| Body rows | `divide-y divide-outline-variant/30 font-data-tabular` |
| Body cell | `px-6 py-4` |
| Row hover | `hover:bg-surface-container-low/30 transition-colors` |
| Líneas verticales | **No usar** |

### 6.5 Badges / Chips / Estados

| Tipo | Clase | Estilo |
|------|-------|--------|
| Badge estándar | `px-2 py-1 bg-surface-container rounded text-[11px] font-bold uppercase tracking-tighter` | Fondo `surface-container`, texto de 11px |
| Indicador de estado | Sin clase específica | Círculo de 8px (`w-2 h-2 bg-error rounded-full`) |

### 6.6 Sidebar (navegación)

| Elemento | Estilo |
|----------|--------|
| Contenedor | `fixed left-0 top-0 h-full w-64 bg-secondary border-r border-outline-variant` |
| Fondo | `#3e2c1c` (secondary) |
| Logo / Título | `font-headline-md text-headline-md text-primary-fixed uppercase tracking-wider` |
| Items de nav (inactivo) | `flex items-center gap-3 px-4 py-3 text-secondary-fixed-dim hover:text-primary-fixed hover:bg-on-secondary-fixed-variant/10` |
| Items de nav (activo) | `text-primary-fixed font-bold border-l-4 border-primary-fixed bg-on-secondary-fixed-variant/20` |
| Nav separación | `space-y-1` (4px gap entre items) |
| Padding interior | `px-2` (8px) |
| Padding de ítem | `px-4 py-3` (16px horizontal, 12px vertical) |
| Iconos | `material-symbols-outlined` |
| Footer (usuario) | `px-6 py-4 flex items-center gap-3 border-t border-outline-variant/30` |
| Avatar | `w-8 h-8 rounded-full bg-primary-fixed flex items-center justify-center text-primary` |

### 6.7 Header (TopAppBar)

| Elemento | Estilo |
|----------|--------|
| Contenedor | `sticky top-0 z-40 bg-surface border-b border-outline-variant flex justify-between items-center px-margin-desktop py-sm` |
| Altura | `py-sm` (12px) + contenido |
| Search area | Input con icono `search` a la izquierda, `flex-1 max-w-xl` |
| Acciones derecha | Iconos + separador vertical + perfil |

### 6.8 Dropzone (subida de archivos)

| Elemento | Estilo |
|----------|--------|
| Contenedor | `border-2 border-dashed border-outline-variant group-hover:border-primary` |
| Icono | `material-symbols-outlined text-primary text-[48px]` — `cloud_upload` |
| Texto | `font-headline-md text-headline-md text-on-surface text-center` |
| Botón CTA | `bg-primary text-on-primary px-8 py-3 font-label-md uppercase tracking-widest` |
| Hover | `group-hover:bg-surface-container-low transition-colors duration-300` |

### 6.9 Paginación

| Elemento | Estilo |
|----------|--------|
| Contenedor | `p-4 border-t border-outline-variant flex justify-between items-center bg-surface-container-low/20` |
| Botones | `p-2 border border-outline-variant hover:bg-surface-container transition-colors disabled:opacity-30` |
| Info | `font-label-md text-on-surface-variant` |

---

## 7. Iconografía

| Propiedad | Valor |
|-----------|-------|
| Sistema | **Material Symbols** (Google) |
| Estilo | **Outlined** (lineales) — `FILL 0` |
| Pesos de stroke | **400** (regular) |
| Carga | CDN: `https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined` |
| Clase base | `material-symbols-outlined` |
| CSS | `font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;` |
| Tamaños usados | `text-sm` (14px), `text-[48px]`, tamaño por defecto (24px) |

Iconos observados en las pantallas:

| Icono | Uso |
|-------|-----|
| `analytics` | Comparador de precios |
| `cloud` | Tiempo en Toledo |
| `calendar_today` | Festividades |
| `edit_calendar` | Reservas manuales |
| `monitoring` | Precios de competencia (activo) |
| `payments` | Costes reales |
| `hotel_class` | Ocupación e incidencias |
| `settings` | Configuración |
| `search` | Búsqueda |
| `calendar_month` | Botón calendario (header) |
| `notifications` | Notificaciones (con badge) |
| `cloud_upload` | Subida de archivos |
| `history` | Histórico / estado |
| `refresh` | Actualizar |
| `date_range` | Rango de fechas |
| `bed` | Tipo de habitación |
| `apartment` | Hotel/competencia |
| `expand_more` | Expandir dropdown |
| `filter_list` | Filtrar |
| `arrow_upward` | Diferencia positiva (precio mayor) |
| `arrow_downward` | Diferencia negativa (precio menor) |
| `chevron_left` / `chevron_right` | Paginación |

---

## 8. Breakpoints responsive

| Rango | Columnas | Márgenes | Headline |
|-------|----------|----------|----------|
| **Desktop** (1440px+) | 12 | `margin-desktop`: 40px | `headline-lg` (32px) |
| **Tablet** (768–1439px) | 8 | 24px | `headline-lg` (32px) |
| **Mobile** (0–767px) | 4 | `margin-mobile`: 16px | `headline-lg-mobile` (28px) |

---

## 9. Tailwind Configuration

El archivo `tailwind.config.js` completo con todos los tokens del sistema de diseño está en la raíz del proyecto junto a este documento.
