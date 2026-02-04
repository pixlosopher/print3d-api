"""
Test script for the new cost-efficient flow.

New flow:
1. Generate 2D concept only (~$0.001 with Gemini)
2. User reviews preview
3. User selects options (size, material, color, mesh style)
4. User pays
5. THEN generate 3D (~$0.30 with Meshy) - only after payment!
6. Submit to Shapeways
"""

import sys
sys.path.insert(0, 'web')

from api import app


def test_new_flow():
    print("=" * 60)
    print("TESTING NEW COST-EFFICIENT FLOW")
    print("=" * 60)

    with app.test_client() as client:
        # ===== STEP 1: Get available options =====
        print("\n[1] GET /api/options - Available customization options")
        response = client.get('/api/options')
        assert response.status_code == 200
        data = response.get_json()

        print(f"    Sizes: {list(data['sizes'].keys())}")
        print(f"    Materials: {list(data['materials'].keys())}")
        print(f"    Mesh styles: {list(data['mesh_styles'].keys())}")

        # ===== STEP 2: Generate 2D concept only =====
        print("\n[2] POST /api/generate - Generate 2D concept (CHEAP)")
        response = client.post('/api/generate', json={
            'prompt': 'A futuristic spaceship miniature',
            'style': 'figurine'
        })
        assert response.status_code == 201
        data = response.get_json()
        job_id = data['job_id']

        print(f"    Job ID: {job_id}")
        print(f"    Status: {data['status']}")
        assert job_id.startswith('concept_'), "Job should be concept-only"
        print("    ✅ Concept job created (NO 3D generation yet!)")

        # ===== STEP 3: Calculate price =====
        print("\n[3] POST /api/price - Calculate price for configuration")

        # Test various configurations
        configs = [
            {"material": "plastic_white", "size": "mini"},
            {"material": "plastic_color", "size": "medium", "color": "blue"},
            {"material": "full_color", "size": "large"},
            {"material": "resin_premium", "size": "medium", "color": "clear"},
            {"material": "metal_steel", "size": "xl", "color": "silver"},
        ]

        for config in configs:
            response = client.post('/api/price', json=config)
            assert response.status_code == 200
            data = response.get_json()
            mat = config['material']
            size = config['size']
            color = config.get('color', 'N/A')
            print(f"    {mat} + {size} + {color}: {data['total_display']}")

        # ===== STEP 4: Validate config =====
        print("\n[4] POST /api/validate-config - Validate before checkout")

        # Test invalid: missing required color
        response = client.post('/api/validate-config', json={
            'material': 'plastic_color',
            'size': 'medium'
        })
        assert response.status_code == 400
        data = response.get_json()
        print(f"    Missing color: valid={data.get('valid', False)}, error={data.get('error')}")

        # Test valid config
        response = client.post('/api/validate-config', json={
            'material': 'plastic_color',
            'size': 'medium',
            'color': 'red',
            'mesh_style': 'detailed'
        })
        assert response.status_code == 200
        data = response.get_json()
        print(f"    With color: valid={data['valid']}, price={data['price']['total_display']}")

        # ===== STEP 5: Price matrix =====
        print("\n[5] Price Matrix (from /api/options)")
        response = client.get('/api/options')
        data = response.get_json()

        print("\n    PRICE MATRIX (USD):")
        print("    " + "-" * 60)
        header = "    Material            | mini  | small | medium | large  | xl"
        print(header)
        print("    " + "-" * 60)

        for row in data['price_matrix']:
            mat_name = row['material']['name'][:18].ljust(18)
            prices = row['prices']
            mini = prices.get('mini', {}).get('display', '-')
            small = prices.get('small', {}).get('display', '-')
            medium = prices.get('medium', {}).get('display', '-')
            large = prices.get('large', {}).get('display', '-')
            xl = prices.get('xl', {}).get('display', '-')
            print(f"    {mat_name} | {mini:5} | {small:5} | {medium:6} | {large:6} | {xl:5}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nNEW FLOW SUMMARY:")
    print("1. /api/generate → Creates concept job (2D only)")
    print("2. /api/options  → Get sizes, materials, mesh styles")
    print("3. /api/price    → Calculate price for configuration")
    print("4. /api/checkout → Create Stripe session (with color, mesh_style)")
    print("5. Stripe webhook → Triggers 3D generation AFTER payment")
    print("6. 3D model sent to Shapeways for printing")
    print("\nCOST SAVINGS:")
    print("- Before: ~$0.30/abandoned user (wasted Meshy API calls)")
    print("- After:  ~$0.001/abandoned user (only Gemini 2D)")
    print("- Savings: 99.7% reduction in abandoned user costs!")


if __name__ == "__main__":
    test_new_flow()
