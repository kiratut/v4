# // TEMP: Test deduplication functionality
"""
Test script for vacancy deduplication using content_hash
- Tests enhanced content_hash algorithm (SHA256)
- Tests deduplication in database layer
- Tests edge cases and variations
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.models import Vacancy
from core.task_database import TaskDatabase
import tempfile
import json

def test_content_hash_algorithm():
    """Test the enhanced content_hash algorithm"""
    print("🔧 Testing Enhanced Content Hash Algorithm...")
    
    # Test basic vacancy
    vacancy1 = Vacancy(
        hh_id="123456",
        title="Python Developer",
        employer_name="Test Company",
        employer_id="1234",
        salary_from=100000,
        salary_to=150000,
        currency="RUR",
        experience="between1And3",
        schedule="fullDay",
        employment="full",
        key_skills=["Python", "Django", "PostgreSQL"],
        description="We are looking for a Python developer to join our team.",
        area="Moscow"
    )
    
    hash1 = vacancy1.calculate_hash()
    print(f"  Hash 1: {hash1}")
    print(f"  Hash length: {len(hash1)} chars")
    
    # Test identical vacancy (should have same hash)
    vacancy2 = Vacancy(
        hh_id="654321",  # Different HH ID
        title="Python Developer",
        employer_name="Test Company",
        employer_id="1234",
        salary_from=100000,
        salary_to=150000,
        currency="RUR",
        experience="between1And3",
        schedule="fullDay",
        employment="full",
        key_skills=["Python", "Django", "PostgreSQL"],
        description="We are looking for a Python developer to join our team.",
        area="Moscow"
    )
    
    hash2 = vacancy2.calculate_hash()
    print(f"  Hash 2: {hash2}")
    
    if hash1 == hash2:
        print("  ✅ Identical content produces same hash")
    else:
        print("  ❌ Identical content produces different hashes")
    
    # Test with case differences (should be same due to normalization)
    vacancy3 = Vacancy(
        hh_id="789123",
        title="PYTHON DEVELOPER",  # Different case
        employer_name="TEST COMPANY",  # Different case
        employer_id="1234",
        salary_from=100000,
        salary_to=150000,
        currency="rur",  # Different case
        experience="between1And3",
        schedule="fullDay",
        employment="full",
        key_skills=["PYTHON", "Django", "postgresql"],  # Mixed case
        description="We are looking for a Python developer to join our team.",
        area="moscow"  # Different case
    )
    
    hash3 = vacancy3.calculate_hash()
    print(f"  Hash 3 (case diff): {hash3}")
    
    if hash1 == hash3:
        print("  ✅ Case normalization works correctly")
    else:
        print("  ❌ Case normalization failed")
    
    # Test with skill order differences (should be same due to sorting)
    vacancy4 = Vacancy(
        hh_id="456789",
        title="Python Developer",
        employer_name="Test Company",
        employer_id="1234",
        salary_from=100000,
        salary_to=150000,
        currency="RUR",
        experience="between1And3",
        schedule="fullDay",
        employment="full",
        key_skills=["PostgreSQL", "Django", "Python"],  # Different order
        description="We are looking for a Python developer to join our team.",
        area="Moscow"
    )
    
    hash4 = vacancy4.calculate_hash()
    print(f"  Hash 4 (skills reordered): {hash4}")
    
    if hash1 == hash4:
        print("  ✅ Skill sorting works correctly")
    else:
        print("  ❌ Skill sorting failed")
    
    # Test with different content (should have different hash)
    vacancy5 = Vacancy(
        hh_id="111222",
        title="Java Developer",  # Different title
        employer_name="Test Company",
        employer_id="1234",
        salary_from=100000,
        salary_to=150000,
        currency="RUR",
        experience="between1And3",
        schedule="fullDay",
        employment="full",
        key_skills=["Java", "Spring", "MySQL"],  # Different skills
        description="We are looking for a Java developer to join our team.",
        area="Moscow"
    )
    
    hash5 = vacancy5.calculate_hash()
    print(f"  Hash 5 (different content): {hash5}")
    
    if hash1 != hash5:
        print("  ✅ Different content produces different hash")
    else:
        print("  ❌ Different content produces same hash")
    
    print("✅ Content hash algorithm test completed")

def test_database_deduplication():
    """Test deduplication in database layer"""
    print("\n🔧 Testing Database Deduplication...")
    
    # Use temporary database
    with tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        db = TaskDatabase(db_path=db_path)
        
        # Create test vacancy
        vacancy1 = Vacancy(
            hh_id="TEST001",
            title="Senior Python Developer",
            employer_name="Tech Corp",
            salary_from=120000,
            salary_to=180000,
            currency="RUR",
            experience="between3And6",
            schedule="remote",
            employment="full",
            key_skills=["Python", "FastAPI", "Docker"],
            description="Looking for senior Python developer with 3+ years experience.",
            area="Saint Petersburg"
        )
        
        # Save first vacancy
        result1 = db.save_vacancy(vacancy1)
        print(f"  First save result: {result1}")
        
        # Try to save identical vacancy with different HH ID
        vacancy2 = Vacancy(
            hh_id="TEST002",  # Different HH ID
            title="Senior Python Developer",
            employer_name="Tech Corp",
            salary_from=120000,
            salary_to=180000,
            currency="RUR",
            experience="between3And6",
            schedule="remote",
            employment="full",
            key_skills=["Python", "FastAPI", "Docker"],
            description="Looking for senior Python developer with 3+ years experience.",
            area="Saint Petersburg"
        )
        
        result2 = db.save_vacancy(vacancy2)
        print(f"  Second save result (duplicate): {result2}")
        
        # Check total count
        stats = db.get_stats()
        total_vacancies = stats['total_vacancies']
        print(f"  Total vacancies in DB: {total_vacancies}")
        
        if total_vacancies == 1:
            print("  ✅ Deduplication prevented duplicate insertion")
        else:
            print(f"  ❌ Deduplication failed, expected 1 vacancy, got {total_vacancies}")
        
        # Test with slightly different content (should create new vacancy)
        vacancy3 = Vacancy(
            hh_id="TEST003",
            title="Senior Python Developer",
            employer_name="Tech Corp",
            employer_id="7890",
            salary_from=130000,  # Different salary
            salary_to=190000,    # Different salary
            currency="RUR",
            experience="between3And6",
            schedule="remote",
            employment="full",
            key_skills=["Python", "FastAPI", "Docker"],
            description="Looking for senior Python developer with 3+ years experience.",
            area="Saint Petersburg"
        )
        
        result3 = db.save_vacancy(vacancy3)
        print(f"  Third save result (different salary): {result3}")
        
        stats2 = db.get_stats()
        total_vacancies2 = stats2['total_vacancies']
        print(f"  Total vacancies after salary change: {total_vacancies2}")
        
        if total_vacancies2 == 2:
            print("  ✅ Different content created new vacancy")
        else:
            print(f"  ❌ Expected 2 vacancies, got {total_vacancies2}")
        
        print("✅ Database deduplication test completed")
        
    finally:
        # Clean up temporary database
        Path(db_path).unlink(missing_ok=True)

def test_edge_cases():
    """Test edge cases for deduplication"""
    print("\n🔧 Testing Edge Cases...")
    
    # Test with None/empty values
    vacancy_empty = Vacancy(
        hh_id="EDGE001",
        title="Test Vacancy",
        employer_name="",  # Empty
        employer_id="",    # Empty
        salary_from=None,  # None
        salary_to=None,    # None
        currency=None,     # None
        experience=None,   # None
        schedule=None,     # None
        employment=None,   # None
        key_skills=None,   # None
        description=None,  # None
        area=None          # None
    )
    
    hash_empty = vacancy_empty.calculate_hash()
    print(f"  Hash with None/empty values: {hash_empty}")
    
    # Test with whitespace
    vacancy_whitespace = Vacancy(
        hh_id="EDGE002",
        title="  Test Vacancy  ",  # With whitespace
        employer_name="   ",       # Only whitespace
        salary_from=None,
        salary_to=None,
        currency=None,
        experience=None,
        schedule=None,
        employment=None,
        key_skills=["  Python  ", "  Django  "],  # Skills with whitespace
        description="   Some description   ",
        area="  Moscow  "
    )
    
    hash_whitespace = vacancy_whitespace.calculate_hash()
    print(f"  Hash with whitespace: {hash_whitespace}")
    
    # Test with very long description (should be truncated)
    long_description = "A" * 1000  # 1000 characters
    vacancy_long = Vacancy(
        hh_id="EDGE003",
        title="Test Vacancy",
        employer_name="Test Company",
        employer_id="1234",
        description=long_description
    )
    
    hash_long = vacancy_long.calculate_hash()
    print(f"  Hash with long description: {hash_long}")
    
    # Test with very long description truncated
    vacancy_long2 = Vacancy(
        hh_id="EDGE004",
        title="Test Vacancy",
        employer_name="Test Company",
        employer_id="1234",
        description=long_description + "EXTRA"  # Slightly longer
    )
    
    hash_long2 = vacancy_long2.calculate_hash()
    print(f"  Hash with slightly longer description: {hash_long2}")
    
    if hash_long == hash_long2:
        print("  ✅ Description truncation works correctly")
    else:
        print("  ❌ Description truncation failed")
    
    # Test with special characters
    vacancy_special = Vacancy(
        hh_id="EDGE005",
        title="Python/Django разработчик",  # Russian + special chars
        employer_name="Компания 'Тест' & Co",
        employer_id="5555",
        description="Работа с API, JSON, XML и прочими технологиями...",
        key_skills=["Python/Django", "REST API", "PostgreSQL/MongoDB"],
        area="Санкт-Петербург"
    )
    
    hash_special = vacancy_special.calculate_hash()
    print(f"  Hash with special characters: {hash_special}")
    
    print("✅ Edge cases test completed")

def benchmark_hashing():
    """Benchmark hashing performance"""
    print("\n🔧 Benchmarking Hash Performance...")
    
    import time
    
    # Create test vacancy
    vacancy = Vacancy(
        hh_id="BENCH001",
        title="Performance Test Developer",
        employer_name="Benchmark Corp",
        employer_id="9999",
        salary_from=100000,
        salary_to=150000,
        currency="RUR",
        experience="between1And3",
        schedule="fullDay",
        employment="full",
        key_skills=["Python", "Performance", "Testing", "Optimization"],
        description="Looking for a developer to work on performance optimization projects.",
        area="Moscow"
    )
    
    # Benchmark hashing
    iterations = 1000
    start_time = time.time()
    
    for i in range(iterations):
        vacancy.calculate_hash()
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / iterations
    
    print(f"  Iterations: {iterations}")
    print(f"  Total time: {total_time:.4f}s")
    print(f"  Average time per hash: {avg_time*1000:.4f}ms")
    print(f"  Hashes per second: {iterations/total_time:.0f}")
    
    if avg_time < 0.001:  # Less than 1ms
        print("  ✅ Hash performance is acceptable")
    else:
        print("  ⚠️  Hash performance might be slow for large datasets")
    
    print("✅ Hash performance benchmark completed")

if __name__ == "__main__":
    print("Vacancy Deduplication Test Suite")
    print("=" * 50)
    
    test_content_hash_algorithm()
    test_database_deduplication()
    test_edge_cases()
    benchmark_hashing()
    
    print("\n🎉 All deduplication tests completed!")
    print("\nNext steps:")
    print("1. Monitor deduplication effectiveness in production")
    print("2. Add periodic cleanup of old duplicates")
    print("3. Implement duplicate analysis tools")
