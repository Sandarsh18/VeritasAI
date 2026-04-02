import asyncio
from agents import decompose_claim

async def test_decomposition():
    """
    Tests the claim decomposition functionality.
    """
    print("--- Testing Claim Decomposition ---")
    
    claim = "vaccines cause autism and the moon landing was faked"
    sub_claims = await decompose_claim(claim)
    
    print(f"Original claim: '{claim}'")
    print(f"Decomposed into: {sub_claims}")
    
    assert len(sub_claims) == 2
    assert "vaccines cause autism" in sub_claims[0].lower()
    assert "moon landing was faked" in sub_claims[1].lower()
    
    print("--- Claim decomposition test passed! ---")

if __name__ == "__main__":
    asyncio.run(test_decomposition())
