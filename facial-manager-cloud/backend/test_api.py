"""
Script de teste para Pontix Cloud API.

Testa todos os endpoints com dados mock.

Uso:
    python test_api.py
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

# Configurações
API_BASE_URL = "http://localhost:8001"
HEADERS = {
    "Content-Type": "application/json",
}

# Token de teste (será obtido do login)
TEST_TOKEN = None
TEST_COMPANY_ID = None
TEST_EMPLOYEE_ID = None


async def test_health():
    """Testa endpoint de health."""
    print("\n" + "=" * 60)
    print("TEST: Health Check")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200, "Health check failed"
        print("✓ Health check passed")


async def test_register():
    """Testa registro de novo usuário."""
    global TEST_TOKEN
    
    print("\n" + "=" * 60)
    print("TEST: Register New User")
    print("=" * 60)
    
    payload = {
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "company_name": "Test Company",
        "cnpj": "12.345.678/0001-00",
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/auth/register",
            json=payload,
            headers=HEADERS,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 201, f"Registration failed: {response.text}"
        
        data = response.json()
        TEST_TOKEN = data["access_token"]
        print(f"✓ Registration successful. Token obtained: {TEST_TOKEN[:20]}...")


async def test_login():
    """Testa login de usuário."""
    global TEST_TOKEN
    
    print("\n" + "=" * 60)
    print("TEST: Login")
    print("=" * 60)
    
    payload = {
        "email": "test@example.com",
        "password": "password",
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/auth/login",
            json=payload,
            headers=HEADERS,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        if not TEST_TOKEN:  # Se não tem token do registro, usa do login
            TEST_TOKEN = data["access_token"]
        print(f"✓ Login successful. Token: {data['access_token'][:20]}...")


async def test_get_current_user():
    """Testa obtenção de usuário atual."""
    print("\n" + "=" * 60)
    print("TEST: Get Current User")
    print("=" * 60)
    
    if not TEST_TOKEN:
        print("⚠ Skipped: No token available")
        return
    
    headers = {**HEADERS, "Authorization": f"Bearer {TEST_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/auth/me",
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            print("✓ Get current user successful")
        else:
            print(f"Error: {response.text}")


async def test_accounting_dashboard():
    """Testa dashboard do contador."""
    print("\n" + "=" * 60)
    print("TEST: Accounting Dashboard")
    print("=" * 60)
    
    if not TEST_TOKEN:
        print("⚠ Skipped: No token available")
        return
    
    headers = {**HEADERS, "Authorization": f"Bearer {TEST_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/accounting/dashboard",
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 403]:  # 403 se sem empresa
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            print("✓ Accounting dashboard request processed")
        else:
            print(f"Error: {response.text}")


async def test_accounting_employees():
    """Testa listagem de funcionários."""
    print("\n" + "=" * 60)
    print("TEST: Accounting - List Employees")
    print("=" * 60)
    
    if not TEST_TOKEN:
        print("⚠ Skipped: No token available")
        return
    
    headers = {**HEADERS, "Authorization": f"Bearer {TEST_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/accounting/employees?page=1&page_size=10",
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 403]:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, default=str)}")
            print("✓ Employees list request processed")
        else:
            print(f"Error: {response.text}")


async def test_accounting_occurrences():
    """Testa listagem de ocorrências."""
    print("\n" + "=" * 60)
    print("TEST: Accounting - List Occurrences")
    print("=" * 60)
    
    if not TEST_TOKEN:
        print("⚠ Skipped: No token available")
        return
    
    headers = {**HEADERS, "Authorization": f"Bearer {TEST_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/accounting/occurrences?page=1&page_size=10",
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code in [200, 403]:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, default=str)}")
            print("✓ Occurrences list request processed")
        else:
            print(f"Error: {response.text}")


async def test_owner_dashboard():
    """Testa dashboard do proprietário."""
    print("\n" + "=" * 60)
    print("TEST: Owner Dashboard")
    print("=" * 60)
    
    if not TEST_TOKEN:
        print("⚠ Skipped: No token available")
        return
    
    headers = {**HEADERS, "Authorization": f"Bearer {TEST_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/owner/dashboard",
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, default=str)}")
            print("✓ Owner dashboard request processed")
        else:
            print(f"Error: {response.text}")


async def test_owner_companies():
    """Testa listagem de empresas."""
    print("\n" + "=" * 60)
    print("TEST: Owner - List Companies")
    print("=" * 60)
    
    if not TEST_TOKEN:
        print("⚠ Skipped: No token available")
        return
    
    headers = {**HEADERS, "Authorization": f"Bearer {TEST_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/api/owner/companies?page=1&page_size=10",
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, default=str)}")
            
            # Salva o primeiro company_id se encontrar
            if data.get('items'):
                global TEST_COMPANY_ID
                TEST_COMPANY_ID = data['items'][0]['id']
            
            print("✓ Companies list request processed")
        else:
            print(f"Error: {response.text}")


async def test_sync_employees():
    """Testa sincronização de funcionários."""
    print("\n" + "=" * 60)
    print("TEST: Sync - Employees")
    print("=" * 60)
    
    company_id = TEST_COMPANY_ID or str(uuid4())
    
    payload = {
        "company_id": company_id,
        "company_data": {
            "name": "Test Company",
            "cnpj": "12.345.678/0001-00",
            "owner_id": "test-owner",
        },
        "employees": [
            {
                "local_id": "1",
                "user_id": "001",
                "full_name": "Employee 1",
                "email": "emp1@example.com",
                "cpf": "123.456.789-00",
                "department": "TI",
                "role": "Developer",
            },
            {
                "local_id": "2",
                "user_id": "002",
                "full_name": "Employee 2",
                "email": "emp2@example.com",
                "cpf": "123.456.789-01",
                "department": "RH",
                "role": "Manager",
            },
        ],
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Nota: Este endpoint pode não requer autenticação para sincronização do sistema local
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/sync/employees",
            json=payload,
            headers=HEADERS,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print("✓ Employees sync successful")
        else:
            print(f"⚠ Sync returned status {response.status_code}")


async def test_sync_time_records():
    """Testa sincronização de registros de ponto."""
    print("\n" + "=" * 60)
    print("TEST: Sync - Time Records")
    print("=" * 60)
    
    company_id = TEST_COMPANY_ID or str(uuid4())
    today = datetime.now(timezone.utc).date()
    
    payload = {
        "company_id": company_id,
        "time_records": [
            {
                "local_id": "1",
                "user_id": "001",
                "employee_name": "Employee 1",
                "record_date": f"{today}",
                "record_time": "08:30:00",
                "record_type": "entry",
                "source": "device",
            },
            {
                "local_id": "2",
                "user_id": "001",
                "employee_name": "Employee 1",
                "record_date": f"{today}",
                "record_time": "18:00:00",
                "record_type": "exit",
                "source": "device",
            },
        ],
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/sync/time-records",
            json=payload,
            headers=HEADERS,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print("✓ Time records sync successful")
        else:
            print(f"⚠ Sync returned status {response.status_code}")


async def test_sync_occurrences():
    """Testa sincronização de ocorrências."""
    print("\n" + "=" * 60)
    print("TEST: Sync - Occurrences")
    print("=" * 60)
    
    company_id = TEST_COMPANY_ID or str(uuid4())
    today = datetime.now(timezone.utc).date()
    
    payload = {
        "company_id": company_id,
        "occurrences": [
            {
                "user_id": "001",
                "occurrence_date": f"{today}",
                "occurrence_type": "late",
                "severity": "low",
                "description": "Employee arrived 15 minutes late",
            },
        ],
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/api/sync/occurrences",
            json=payload,
            headers=HEADERS,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            print("✓ Occurrences sync successful")
        else:
            print(f"⚠ Sync returned status {response.status_code}")


async def run_all_tests():
    """Executa todos os testes."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  PONTIX CLOUD API - TEST SUITE".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    
    tests = [
        ("Health Check", test_health),
        ("Register", test_register),
        ("Login", test_login),
        ("Get Current User", test_get_current_user),
        ("Accounting Dashboard", test_accounting_dashboard),
        ("Accounting Employees", test_accounting_employees),
        ("Accounting Occurrences", test_accounting_occurrences),
        ("Owner Dashboard", test_owner_dashboard),
        ("Owner Companies", test_owner_companies),
        ("Sync Employees", test_sync_employees),
        ("Sync Time Records", test_sync_time_records),
        ("Sync Occurrences", test_sync_occurrences),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("=" * 60)
    
    if failed == 0:
        print("\n✓ All tests passed!")
    else:
        print(f"\n✗ {failed} test(s) failed")


if __name__ == "__main__":
    print("Starting Pontix Cloud API tests...")
    print(f"Target: {API_BASE_URL}")
    
    asyncio.run(run_all_tests())
