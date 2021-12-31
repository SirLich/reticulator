import unittest
import sys

sys.path.insert(0, '../reticulator')
from reticulator import *

def get_packs():
    project = Project('./content/bp/', './content/rp/')
    return project.behavior_pack, project.resource_pack

def create_output_directory():
    os.mkdir('test_output')

def clean_up_output_directory():
    os.remove('test_output')

class TestFunctions(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_count(self):
        self.assertEqual(len(self.bp.functions), 2)

    def test_comment_stripping(self):
        """
        The first function has 1 command, the second has 2
        """
        self.assertEqual(len(self.bp.functions[0].commands), 2)
        self.assertEqual(len(self.bp.functions[1].commands), 1)
    
    def test_getting_function(self):
        self.assertTrue(self.bp.get_function('functions\\kill_all_safe.mcfunction'))
        self.assertTrue(self.bp.get_function('functions\\teleport\\home.mcfunction'))

    
class TestRecipes(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_files(self):
        self.assertEqual(len(self.bp.recipes), 5)

    def test_get(self):
        """
        Test all possible recipe types.
        """
        self.assertEqual(self.bp.get_recipe("minecraft:acacia_boat").identifier, "minecraft:acacia_boat")
        self.assertEqual(self.bp.get_recipe("minecraft:andesite").identifier, "minecraft:andesite")
        self.assertEqual(self.bp.get_recipe("minecraft:brew_awkward_blaze_powder").identifier, "minecraft:brew_awkward_blaze_powder")
        self.assertEqual(self.bp.get_recipe("minecraft:brew_splash_potion_dragon_breath").identifier, "minecraft:brew_splash_potion_dragon_breath")
        self.assertEqual(self.bp.get_recipe("minecraft:furnace_stained_hardened_clay3").identifier, "minecraft:furnace_stained_hardened_clay3")

        with self.assertRaises(AssetNotFoundError):
            self.bp.get_recipe('no fount')

class TestDirty(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
        self.entity = self.bp.get_entity('minecraft:dolphin')

    def test_property(self):
        self.assertEqual(self.entity.dirty, False)
        self.entity.identifier = 'bob'
        self.assertEqual(self.entity.dirty, True)

    def test_jsonpath(self):
        self.assertEqual(self.entity.dirty, False)
        self.entity.set_jsonpath('new_key', {})
        self.assertEqual(self.entity.dirty, True)

    def test_data(self):
        self.assertEqual(self.entity.dirty, False)
        self.entity.data['new_key'] = []
        self.assertEqual(self.entity.dirty, True)

    def test_subresource(self):
        component = self.entity.get_component('minecraft:type_family')
        self.assertEqual(self.entity.dirty, False)
        self.assertEqual(component.dirty, False)

        component.set_jsonpath('new_key', "")

        self.assertEqual(self.entity.dirty, True)
        self.assertEqual(component.dirty, True)

    @unittest.skip("id-based dirty is not implemented")
    def test_subresource_id(self):
        component = self.entity.get_component('minecraft:type_family')
        self.assertEqual(self.entity.dirty, False)
        self.assertEqual(component.dirty, False)

        component.id = 'new_component_name'

        self.assertEqual(self.entity.dirty, True)
        self.assertEqual(component.dirty, True)

class TestParticle(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_particle_properties(self):
        """
        Checks that the properties of the test particle is correct.
        """
        particle = self.rp.get_particle('minecraft:death_explosion_emitter')
        self.assertEqual(particle.identifier, 'minecraft:death_explosion_emitter')
        self.assertEqual(particle.format_version, "1.10.0")

    def test_particle_path(self):
        """
        Checks whether the FileResource properties are correct.
        """
        self.assertEqual(len(self.rp.particles), 2)
        particle = self.rp.get_particle('minecraft:death_explosion_emitter')
        self.assertEqual(particle.file_name, 'explosion_death.json')
        self.assertEqual(particle.file_path, 'particles\\explosions\\explosion_death.json')

    def test_particle_subresources(self):
        """
        Tests access into the 'components' property of the particle.
        """ 
        particle = self.rp.get_particle('minecraft:death_explosion_emitter')
        self.assertEqual(len(particle.components), 10)
        component = particle.get_component('minecraft:emitter_rate_instant')
        self.assertEqual(component.id, 'minecraft:emitter_rate_instant')
        self.assertEqual(component.get_jsonpath('num_particles'), 20)
        self.assertEqual(component.data['num_particles'], 20)

class TestJsonPathAccess(unittest.TestCase):
    """
    Test various jsonpath access methods.
    """

    def setUp(self) -> None:
        self.project = Project('./content/bp/', './content/rp/')
        self.bp = self.project.behavior_pack
        self.rp = self.project.resource_pack
        
    def test_get_jsonpath(self):
        """
        Tests the result of a valid jsonpath.
        """

        # Set up
        dolphin = self.bp.get_entity('minecraft:dolphin')
        egg = self.bp.get_entity('minecraft:egg')

        # Test Property access
        self.assertEqual(dolphin.identifier, 'minecraft:dolphin')

        # Test jsonpath access
        self.assertEqual(
            len(dolphin.get_jsonpath('minecraft:entity/component_groups')), 7
        )

        # Test jsonpath which does not exist
        self.assertEqual(egg.component_groups, [])

        # Test jsonpath default
        self.assertEqual(dolphin.get_jsonpath('dne', default='default'), 'default')

        # Test jsonpath which does not exist
        with self.assertRaises(AssetNotFoundError):
            dolphin.get_jsonpath('dne')

if __name__ == '__main__':
    unittest.main()