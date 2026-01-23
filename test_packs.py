#!/usr/bin/env python3
"""
Test script for Comfy Gimpy Studio Pack System.
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.config import Config
from packs.packager import Packager
from packs.validator import PackValidator
from packs.registry import PackRegistry

async def test_pack_system():
    print('Testing Comfy Gimpy Studio Pack System...')

    try:
        # Initialize components
        config = Config()
        packager = Packager(config)
        validator = PackValidator(config)
        registry = PackRegistry(config)

        print('✓ Components initialized')

        # Test pack creation
        print('Creating test pack...')
        result = await packager.create_pack(
            pack_type='template',
            name='Test Template Pack',
            version='1.0.0',
            description='A test template pack',
            author='Test Author',
            license='MIT',
            tags=['test', 'template'],
            content={'templates': [{'name': 'test_template', 'data': 'test'}]},
            metadata={},
            dependencies=[],
            previews=[]
        )

        print(f'✓ Pack created: {result["pack_id"]}')

        # Test validation
        print('Validating pack...')
        is_valid, errors, manifest = await validator.validate_pack(result['pack_path'])
        print(f'✓ Pack validation: {"PASSED" if is_valid else "FAILED"}')
        if not is_valid:
            print(f'  Errors: {errors}')

        # Test registry
        print('Testing registry...')
        packs = registry.list_packs()
        print(f'✓ Found {len(packs)} packs in registry')

        if packs:
            pack_info = registry.get_pack(packs[0].id)
            print(f'✓ Retrieved pack info: {pack_info.name}')

        print('Pack system test completed successfully!')

    except Exception as e:
        print(f'✗ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == '__main__':
    success = asyncio.run(test_pack_system())
    sys.exit(0 if success else 1)