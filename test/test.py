import unittest
import sys
import functools

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

        # With stripping on
        self.assertEqual(len(self.bp.functions[0].commands), 2)
        self.assertEqual(len(self.bp.functions[1].commands), 1)

        # With stripping off
        # TODO
    
    def test_getting_function(self):
        # Getting function by path can take multiple path formats
        self.assertTrue(self.bp.get_function('functions\\kill_all_safe.mcfunction'))
        self.assertTrue(self.bp.get_function('functions/teleport/home.mcfunction'))

    def test_non_existent_function(self):
        with self.assertRaises(AssetNotFoundError):
            self.bp.get_function('functions/no_function.mcfunction')

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
            self.bp.get_recipe('no found')

class TestDirty(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
        self.entity = self.bp.get_entity('minecraft:dolphin')
        self.function = self.bp.get_function('functions/kill_all_safe.mcfunction')
        self.component = self.entity.get_component('minecraft:type_family')

    def assert_dirties(attribute):
        """
        Wrapper, which ensures that the resource is dirty, after the function is called.
        Attribute is passed in as a string, since `self` context is only available at runtime.
        """
        def _implementation(func):
            @functools.wraps(func)
            def wrapper(self, *args):
                resource = getattr(self, attribute)
                self.assertEqual(resource.dirty, False)
                func(self, *args)
                self.assertEqual(resource.dirty, True)
            return wrapper
        return _implementation


    @assert_dirties('function')
    def test_list_append(self):
        self.function.commands.append('a new command!')

    @assert_dirties('function')
    def test_list_delete(self):
        del self.function.commands[0]

    @assert_dirties('function')
    def test_list_edit(self):
        self.function.commands[0] = 'new command'

    @assert_dirties('entity')
    def test_dict_list_insert(self):
        self.entity.data['new_key'] = []

    @assert_dirties('entity')
    def test_property(self):
        self.entity.identifier = 'bob'

    @assert_dirties('entity')
    def test_jsonpath(self):
        self.entity.set_jsonpath('new_key', {})

    @assert_dirties('entity')
    def test_data(self):
        self.entity.data['new_key'] = []

    @assert_dirties('component')
    @assert_dirties('entity')
    def test_subresource(self):
        self.component.set_jsonpath('new_key', "")

    @assert_dirties('component')
    @assert_dirties('entity')
    def test_subresource_id(self):
        self.component.id = 'new_component_name'

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

class TestEntityFileRP(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
        self.entity = self.rp.get_entity('minecraft:dolphin')

    def test_entity_file_path(self):
        """
        Tests that the entity file path is correct.
        """

        # Check filepath
        self.assertEqual(self.entity.file_path, 'entity\\dolphin.entity.json')

    def test_animations(self):
        """
        Tests the key-value pair situation
        """

        animations = self.entity.animations
        self.assertEqual(len(animations), 1)

        animation = animations[0]
        self.assertEqual(animation.shortname, 'move')
        self.assertEqual(animation.resource.id, 'animation.dolphin.move')

class TestJsonPathAccess(unittest.TestCase):
    """
    Test various jsonpath access methods.
    """

    def setUp(self) -> None:
        self.project = Project('./content/bp/', './content/rp/')
        self.bp = self.project.behavior_pack
        self.rp = self.project.resource_pack
    
    def test_jsonpath_exists(self):
        """
        Test jsonpath_exists method.
        """

        entity = self.bp.get_entity('minecraft:dolphin')

        # Test exists
        self.assertTrue(entity.jsonpath_exists('minecraft:entity/description/identifier'))

        # Test does not exist
        self.assertFalse(entity.jsonpath_exists('dne'))

    def test_delete_jsonpath(self):
        """ 
        Tests deleting paths from json data.
        """
        entity = self.bp.get_entity('minecraft:dolphin')

        # Delete, with ensure_exists
        with self.assertRaises(AssetNotFoundError):
            entity.delete_jsonpath('dne', ensure_exists=True)
        
        # Delete, without ensure_exists (should not error!)
        entity.delete_jsonpath('dne')

        # Delete string
        entity.delete_jsonpath('minecraft:entity/description/identifier')
        self.assertFalse(entity.jsonpath_exists('minecraft:entity/description/identifier'))

        # Delete complex structure
        entity.delete_jsonpath('minecraft:entity')
        self.assertFalse(entity.jsonpath_exists('minecraft:entity'))

    def test_set_jsonpath(self):
        """
        Test setting a value in a jsonpath.
        """
        entity = self.bp.get_entity('minecraft:dolphin')

        # Test normal set_jsonpath
        entity.set_jsonpath('new_key', 'new_value')
        self.assertEqual(entity.get_jsonpath('new_key'), 'new_value')

        # must_exist=True
        with self.assertRaises(AssetNotFoundError):
            entity.set_jsonpath('does_not_exist', 'new_value', must_exist=True)

        # must_exist=False (implied)
        entity.set_jsonpath('does_not_exist', 'new_value')

        # Test overwrite=False
        entity.set_jsonpath('minecraft:entity/description/identifier', 'minecraft:dog', overwrite=False)
        self.assertNotEqual(entity.get_jsonpath('minecraft:entity/description/identifier'), 'minecraft:dog')

        # Test overwrite=True
        entity.set_jsonpath('minecraft:entity/description/identifier', 'minecraft:dog', overwrite=True)
        self.assertEqual(entity.get_jsonpath('minecraft:entity/description/identifier'), 'minecraft:dog')

    def test_pop_jsonpath(self):
        """
        Tests popping a jsonpath
        """

        entity = self.bp.get_entity('minecraft:dolphin')

        # Test normal pop
        self.assertEqual(entity.pop_jsonpath('minecraft:entity/description/identifier'), 'minecraft:dolphin')
        
        # Test non-existent pop
        with self.assertRaises(AssetNotFoundError):
            entity.pop_jsonpath('dne')

        # Test default
        self.assertEqual(entity.pop_jsonpath('dne', default='default_value'), 'default_value')

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