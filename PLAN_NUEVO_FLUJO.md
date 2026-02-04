# Plan de Implementación: Nuevo Flujo de Generación

## Resumen Ejecutivo

Rediseñar el pipeline para:
1. **Reducir costos** - Generar 3D solo después del pago
2. **Más opciones** - Exponer parámetros de Meshy y Shapeways
3. **Nuevos tamaños** - Rangos más amplios (5cm - 25cm)
4. **Transparencia** - Disclaimer sobre modelo final

---

## Fase 1: Backend - Modelo de Datos

### 1.1 Nuevas opciones de Meshy

```python
# web/models.py o similar

class MeshyOptions:
    model_type: str = "standard"      # "standard" | "lowpoly"
    ai_model: str = "latest"          # "meshy-5" | "meshy-6" | "latest"
    enable_pbr: bool = True           # Texturas PBR
    symmetry_mode: str = "auto"       # "auto" | "on" | "off"
    topology: str = "triangle"        # "quad" | "triangle"
    target_polycount: int = 50000     # 100-300,000
```

### 1.2 Nuevos materiales Shapeways

```python
# web/materials.py

MATERIALS = {
    "plastic_white": {
        "name": "Plástico Blanco",
        "shapeways_id": "TBD",  # Obtener de API
        "base_price_usd": 29,
        "price_multiplier": 1.0,  # Por tamaño
        "colors": None,
        "description": "Económico, acabado mate"
    },
    "plastic_color": {
        "name": "Plástico Color",
        "shapeways_id": "TBD",
        "base_price_usd": 39,
        "price_multiplier": 1.2,
        "colors": ["white", "black", "red", "blue", "green", "yellow", "orange", "pink", "purple"],
        "description": "Elige tu color favorito"
    },
    "resin_premium": {
        "name": "Resina Premium",
        "shapeways_id": "TBD",
        "base_price_usd": 59,
        "price_multiplier": 1.5,
        "colors": ["white", "black", "clear"],
        "description": "Alto detalle, superficie lisa"
    },
    "full_color": {
        "name": "Full Color",
        "shapeways_id": "TBD",  # Full Color Nylon 12
        "base_price_usd": 79,
        "price_multiplier": 2.0,
        "colors": "texture",  # Usa colores del modelo 3D
        "description": "Imprime los colores exactos del diseño"
    },
    "metal_steel": {
        "name": "Metal (Acero)",
        "shapeways_id": "TBD",
        "base_price_usd": 149,
        "price_multiplier": 3.0,
        "colors": ["silver", "bronze"],
        "description": "Acero inoxidable con acabado metálico"
    }
}
```

### 1.3 Nuevos tamaños

```python
# web/sizes.py

SIZES = {
    "mini": {
        "name": "Mini",
        "height_mm": 50,
        "description": "Llavero, escritorio",
        "price_multiplier": 1.0
    },
    "small": {
        "name": "Pequeño",
        "height_mm": 80,
        "description": "Figura de escritorio",
        "price_multiplier": 1.3
    },
    "medium": {
        "name": "Mediano",
        "height_mm": 120,
        "description": "Coleccionable",
        "price_multiplier": 1.8
    },
    "large": {
        "name": "Grande",
        "height_mm": 180,
        "description": "Display / Regalo",
        "price_multiplier": 2.5
    },
    "xl": {
        "name": "XL",
        "height_mm": 250,
        "description": "Pieza de exhibición",
        "price_multiplier": 3.5
    }
}

def calculate_price(material_key: str, size_key: str) -> int:
    """Calcula precio en centavos USD."""
    material = MATERIALS[material_key]
    size = SIZES[size_key]

    base = material["base_price_usd"]
    price = base * size["price_multiplier"] * material["price_multiplier"]

    return int(price * 100)  # Centavos
```

---

## Fase 2: Backend - Nuevo Flujo de API

### 2.1 Endpoint `/api/generate` (MODIFICAR)

**Antes:** Genera imagen + 3D
**Después:** Solo genera imagen 2D

```python
@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Genera solo el concepto 2D (Gemini).
    El 3D se genera después del pago.
    """
    data = request.get_json()
    prompt = data.get("prompt")
    style = data.get("style", "figurine")

    # Solo imagen 2D
    image_result = image_service.generate(prompt, style)

    # Crear job en estado "concept_ready"
    job_id = job_service.create_job(
        prompt=prompt,
        style=style,
        image_url=image_result.url,
        status="concept_ready"  # Nuevo estado
    )

    return jsonify({
        "job_id": job_id,
        "image_url": image_result.url,
        "status": "concept_ready",
        "message": "Concepto generado. Selecciona opciones para continuar."
    })
```

### 2.2 Endpoint `/api/options` (NUEVO)

```python
@app.route("/api/options")
def get_options():
    """Retorna todas las opciones disponibles."""
    return jsonify({
        "sizes": SIZES,
        "materials": MATERIALS,
        "mesh_styles": {
            "standard": {
                "name": "Detallado",
                "description": "Más realista, más polígonos"
            },
            "lowpoly": {
                "name": "Estilizado",
                "description": "Low-poly, aspecto limpio"
            }
        }
    })
```

### 2.3 Endpoint `/api/price` (NUEVO)

```python
@app.route("/api/price", methods=["POST"])
def calculate_price():
    """Calcula precio basado en opciones."""
    data = request.get_json()
    material = data.get("material")
    size = data.get("size")

    price_cents = calculate_price(material, size)

    return jsonify({
        "price_cents": price_cents,
        "price_display": f"${price_cents / 100:.2f}",
        "currency": "USD"
    })
```

### 2.4 Modificar Webhook de Stripe

```python
@app.route("/api/webhook/stripe", methods=["POST"])
def stripe_webhook():
    # ... verificación ...

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"]["order_id"]
        job_id = session["metadata"]["job_id"]

        # Obtener opciones del pedido
        order = order_service.get_order(order_id)

        # AHORA generamos el 3D (ya tenemos el dinero)
        job = job_service.get_job(job_id)

        meshy_options = MeshOptions(
            model_type=order.mesh_style,      # "standard" o "lowpoly"
            ai_model="latest",
            enable_pbr=order.material == "full_color",
            topology="triangle",
        )

        # Generar 3D con Meshy
        mesh_result = await mesh_generator.from_image_async(
            image_url=job.image_url,
            options=meshy_options,
            output_dir=config.output_dir,
            format="glb"
        )

        # Actualizar job
        job_service.update_job(job_id,
            status="mesh_complete",
            mesh_url=mesh_result.glb_url,
            mesh_path=mesh_result.local_path
        )

        # Enviar a Shapeways
        if shapeways_service.is_available:
            shapeways_result = await shapeways_service.submit_order(
                mesh_path=mesh_result.local_path,
                material_id=MATERIALS[order.material]["shapeways_id"],
                size_mm=SIZES[order.size]["height_mm"],
            )

            order_service.update_shapeways_id(
                order_id=order.id,
                shapeways_order_id=shapeways_result.order_id
            )

        # Email de confirmación
        email_service.send_order_confirmation(
            to_email=order.customer_email,
            order_id=order.id,
            message="¡Tu modelo 3D está siendo creado!"
        )

        return jsonify({"status": "success"})
```

---

## Fase 3: Modelo de Base de Datos

### 3.1 Modificar tabla `orders`

```sql
ALTER TABLE orders ADD COLUMN mesh_style VARCHAR(20) DEFAULT 'standard';
ALTER TABLE orders ADD COLUMN color VARCHAR(20);
ALTER TABLE orders ADD COLUMN meshy_options JSON;
```

### 3.2 Modificar tabla `jobs`

```sql
-- Nuevo estado para jobs
-- Estados: pending, generating_image, concept_ready, generating_mesh, mesh_complete, failed

ALTER TABLE jobs ADD COLUMN concept_image_url TEXT;
ALTER TABLE jobs ADD COLUMN mesh_options JSON;
```

---

## Fase 4: Frontend (Especificación)

### 4.1 Flujo de Pantallas

```
[Pantalla 1: Crear]
    └─> Input de prompt
    └─> Botón "Generar Concepto"

[Pantalla 2: Concepto Generado]
    └─> Imagen 2D del concepto
    └─> ⚠️ Disclaimer: "El modelo final puede variar"
    └─> Botón "Personalizar"

[Pantalla 3: Personalizar]
    └─> Imagen 2D (referencia)
    └─> Selector: Estilo (Detallado / Estilizado)
    └─> Selector: Material (con colores si aplica)
    └─> Selector: Tamaño (5cm - 25cm)
    └─> Precio dinámico
    └─> Botón "Ordenar $XX"

[Pantalla 4: Checkout Stripe]
    └─> Datos de envío
    └─> Pago

[Pantalla 5: Confirmación]
    └─> "¡Gracias! Tu modelo está siendo creado"
    └─> "Recibirás un email cuando esté listo"
    └─> Número de orden
```

### 4.2 Componentes Nuevos

```
components/
├── ConceptPreview.tsx      # Muestra imagen 2D con disclaimer
├── StyleSelector.tsx       # Detallado vs Estilizado
├── MaterialSelector.tsx    # Grid de materiales con precios
├── ColorPicker.tsx         # Selector de color (si material lo permite)
├── SizeSelector.tsx        # Selector visual de tamaños
├── PriceDisplay.tsx        # Precio dinámico
└── DisclaimerBanner.tsx    # Aviso sobre modelo final
```

### 4.3 API Calls desde Frontend

```typescript
// 1. Generar concepto
POST /api/generate
Body: { prompt, style }
Response: { job_id, image_url, status: "concept_ready" }

// 2. Obtener opciones
GET /api/options
Response: { sizes, materials, mesh_styles }

// 3. Calcular precio
POST /api/price
Body: { material, size }
Response: { price_cents, price_display }

// 4. Crear checkout
POST /api/checkout
Body: {
    job_id,
    email,
    material,
    color,      // si aplica
    size,
    mesh_style,
    shipping_address
}
Response: { checkout_url }
```

---

## Fase 5: Migraciones y Datos

### 5.1 Obtener IDs reales de Shapeways

```python
# Script para obtener material IDs
async def fetch_shapeways_materials():
    service = PrintService()
    response = await service._request("GET", "/materials")
    materials = response.json()

    for m in materials:
        print(f"{m['title']}: {m['materialId']}")
```

### 5.2 Migración de base de datos

```python
# migrations/001_add_new_options.py
def upgrade():
    # Agregar columnas nuevas
    op.add_column('orders', sa.Column('mesh_style', sa.String(20)))
    op.add_column('orders', sa.Column('color', sa.String(20)))
    op.add_column('jobs', sa.Column('concept_image_url', sa.Text))
```

---

## Fase 6: Testing

### 6.1 Tests Unitarios

```python
def test_price_calculation():
    # Mini + Plástico blanco = $29
    assert calculate_price("plastic_white", "mini") == 2900

    # XL + Metal = $149 * 3.5 * 3.0 = ~$1,566
    assert calculate_price("metal_steel", "xl") == 156450

def test_generate_concept_only():
    response = client.post("/api/generate", json={"prompt": "robot"})
    assert response.json["status"] == "concept_ready"
    assert "mesh_url" not in response.json  # No 3D aún
```

### 6.2 Test E2E

```
1. Generar concepto → Verificar imagen
2. Seleccionar opciones → Verificar precio
3. Checkout → Verificar sesión Stripe
4. Simular webhook → Verificar generación 3D
5. Verificar envío a Shapeways
```

---

## Orden de Implementación

| # | Tarea | Dependencia | Prioridad |
|---|-------|-------------|-----------|
| 1 | Crear `sizes.py` y `materials.py` | - | Alta |
| 2 | Modificar `/api/generate` (solo imagen) | 1 | Alta |
| 3 | Crear `/api/options` y `/api/price` | 1 | Alta |
| 4 | Modificar modelo de Order | 1 | Alta |
| 5 | Modificar webhook Stripe (generar 3D post-pago) | 2,4 | Alta |
| 6 | Actualizar `/api/checkout` con nuevas opciones | 4 | Alta |
| 7 | Obtener IDs reales de Shapeways | - | Media |
| 8 | Tests unitarios | 1-6 | Media |
| 9 | Frontend: ConceptPreview | 2 | Media |
| 10 | Frontend: Selectores | 3 | Media |
| 11 | Frontend: Checkout actualizado | 6 | Media |
| 12 | Test E2E completo | Todo | Baja |

---

## Estimación de Trabajo

| Fase | Descripción | Complejidad |
|------|-------------|-------------|
| Backend - Datos | Sizes, Materials, Models | Baja |
| Backend - API | Endpoints nuevos/modificados | Media |
| Backend - Webhook | Lógica post-pago | Media |
| Frontend | Nuevas pantallas y componentes | Media-Alta |
| Testing | Unit + E2E | Media |
| **Total** | | **Media** |

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Meshy falla post-pago | Reintentos + notificación manual |
| Usuario no recibe email | Página de status por order_id |
| Precio incorrecto | Validación server-side antes de Stripe |
| Shapeways no tiene material | Fallback a material similar |

---

## Métricas de Éxito

- **Costo por abandono**: $0.30 → $0.001 (reducción 99%)
- **Conversión**: Medir antes/después
- **Ticket promedio**: Más opciones = potencial upsell

