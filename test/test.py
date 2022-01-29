import unittest
import sys
import functools
import shutil

sys.path.insert(0, '../reticulator')
from reticulator import *

def get_packs():
    project = Project('./content/bp/', './content/rp/')
    project.resource_pack.output_path = './out/rp/'
    project.behavior_pack.output_path = './out/bp/'
    return project.behavior_pack, project.resource_pack

def get_saved_packs():
    project = Project('./out/bp/', './out/rp/')
    return project.behavior_pack, project.resource_pack

def prepare_output_directory():
    try:
        shutil.rmtree('./out')
    except OSError as e:
        pass

    os.mkdir('./out')

class TestRenderControllers(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_render_controller_file(self):
        self.assertEqual(len(self.rp.render_controller_files), 1)

    def test_render_controller(self):
        self.assertEqual(len(self.rp.render_controllers), 2)

    def test_get_render_controller(self):
        self.rp.get_render_controller('controller.render.dolphin')

    def test_get_render_controller_file(self):
        self.rp.get_render_controller_file('render_controllers/dolphin.render_controller.json')
    
    def test_internals(self):
        self.assertEqual(self.rp.get_render_controller('controller.render.dolphin').file.format_version, '1.8.0')

class TestLootTables(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_loot_table(self):
        self.assertEqual(len(self.bp.loot_tables), 2)
        self.assertEqual(self.bp.loot_tables[0].file_name, 'dolphin.json')
    
    def test_pools(self):
        self.assertEqual(len(self.bp.loot_tables[0].pools), 1)

    def test_loot_from_entity(self):
        dolphin = self.bp.get_entity('minecraft:dolphin')
        group = dolphin.get_component_group('dolphin_adult')
        component = group.get_component('minecraft:loot')
        table_name = component.data['table']
        loot_table = self.bp.get_loot_table(table_name)
        self.assertEqual(len(loot_table.pools), 1)

class TestSounds(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
    
    def test_sounds(self):
        self.assertEqual(len(self.rp.sounds), 2)
        self.assertEqual(self.rp.sounds[0], 'sounds/bottle/fill_dragonbreath1.fsb')
    
    def test_sounds_file(self):
        with self.assertRaises(AssetNotFoundError):
            self.rp.sounds_file
        
    def test_sound_definitions_file(self):
        self.assertEqual(self.rp.sound_definitions_file.format_version, '1.10.0')

class TestTextures(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_textures(self):
        self.assertEqual(len(self.rp.textures), 5)

    def test_texture_paths(self):
        self.assertEqual(self.rp.textures[0], 'textures/blocks/ancient_debris_top.png')

    def test_get_textures(self):
        self.assertEqual(len(self.rp.get_textures('entity')), 2)
        self.assertEqual(len(self.rp.get_textures('dne')), 0)
        self.assertEqual(len(self.rp.get_textures('')), 5)

    def test_get_textures_trim(self):
        self.assertEqual(self.rp.get_textures('entity', trim_extension=False)[0], 'textures/entity/alex.png')
        self.assertEqual(self.rp.get_textures('entity', trim_extension=True)[0], 'textures/entity/alex')

class TestMaterials(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_material_files(self):
        self.assertEqual(len(self.rp.material_files), 1)

    def test_materials(self):
        self.assertEqual(len(self.rp.materials), 5)

    def test_get_material_file(self):
        self.rp.get_material_file('materials/test.material')
        with self.assertRaises(AssetNotFoundError):
            self.rp.get_material_file('materials/dne.material')

    def test_get_material(self):
        self.rp.get_material('dolphin')
        with self.assertRaises(AssetNotFoundError):
            self.rp.get_material('dne')
    
class TestMaterialTriple(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
        self.dolphin = self.rp.get_entity('minecraft:dolphin')
        self.elder_guardian = self.rp.get_entity('minecraft:elder_guardian')

    def test_existing_resources(self):
        """
        Tests that we can generate and use a ShortnameResourceTriple
        """

        materials = self.dolphin.materials
        self.assertEqual(len(materials), 1)

        material = materials[0]
        self.assertEqual(material, self.dolphin.get_material('default'))
        self.assertEqual(material.shortname, 'default')
        self.assertEqual(material.resource.id, 'dolphin')
        self.assertEqual(material.identifier, 'dolphin')
        self.assertEqual(material.exists(), True)

    def test_missing_resources(self):
        """
        Test the behavior of ShortnameResourceTriple when the resource is missing.
        """

        materials = self.elder_guardian.materials
        self.assertEqual(len(materials), 2)

        # Get the last material, which is missing
        material = materials[1]

        self.assertEqual(material.shortname, 'ghost')
        self.assertEqual(material.identifier, 'guardian_ghost')
        self.assertEqual(material.exists(), False)

        with self.assertRaises(AssetNotFoundError):
            material.resource
    
class TestFunctions(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_count(self):
        self.assertEqual(len(self.bp.functions), 2)

    def test_comment_stripping(self):
        """
        The first function has 1 command, the second has 2
        """

        # With stripping off
        self.assertEqual(len(self.bp.functions[0].commands), 4)
        self.assertEqual(len(self.bp.functions[1].commands), 2)

        # With stripping on
        self.bp.functions[0].strip_comments() # Strips 2 comments from the first function
        self.assertEqual(len(self.bp.functions[0].commands), 2) 
    
    def test_getting_function(self):
        # Getting function by path can take multiple path formats
        self.assertTrue(self.bp.get_function('functions/kill_all_safe.mcfunction'))
        self.assertTrue(self.bp.get_function('functions/teleport/home.mcfunction'))

    def test_non_existent_function(self):
        with self.assertRaises(AssetNotFoundError):
            self.bp.get_function('functions/no_function.mcfunction')

    def test_editing_command(self):
        function = self.bp.functions[0]
        command = function.commands[0]

        self.assertEqual(command.data, '# Remove all entities except players')
        command.data = 'new'
        self.assertEqual(command.data, 'new')

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
        self.command = self.function.commands[0]
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
        self.function.commands[0].data = 'new command'

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

class TestAnimationTriple(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
        self.dolphin = self.rp.get_entity('minecraft:dolphin')
        self.elder_guardian = self.rp.get_entity('minecraft:elder_guardian')

    def test_existing_resources(self):
        """
        Tests that we can generate and use a ShortnameResourceTriple
        """

        animations = self.dolphin.animations
        self.assertEqual(len(animations), 1)

        animation = animations[0]
        self.assertEqual(animation.shortname, 'move')
        self.assertEqual(animation.resource.id, 'animation.dolphin.move')
        self.assertEqual(animation.identifier, 'animation.dolphin.move')
        self.assertEqual(animation.exists(), True)

    def test_missing_resources(self):
        """
        Test the behavior of ShortnameResourceTriple when the resource is missing.
        """

        animations = self.elder_guardian.animations
        self.assertEqual(len(animations), 5)

        # Get the last animation, which is missing
        animation = animations[-1]

        self.assertEqual(animation.shortname, 'missing')
        self.assertEqual(animation.identifier, 'animation.guardian.missing')
        self.assertEqual(animation.exists(), False)

        with self.assertRaises(AssetNotFoundError):
            animation.resource

    def test_saving(self):
        """
        Tests that we can save AnimationTriple
        """

        # Edit the resource
        animation : AnimationTriple = self.dolphin.animations[0]
        animation.shortname = 'new_shortname'
        animation.identifier = 'new_identifier'

        # Save the resource
        prepare_output_directory()
        self.rp.save()

        # Test the saved resource
        out_bp, out_rp = get_saved_packs()
        animation = out_rp.get_entity('minecraft:dolphin').animations[0]

        self.assertEqual(animation.shortname, 'new_shortname')
        self.assertEqual(animation.identifier, 'new_identifier')

        # Raise error for the renamed resource
        with self.assertRaises(AssetNotFoundError):
            self.dolphin.get_animation('move')

class TestEntityFileBP(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
        self.entity = self.bp.get_entity('minecraft:dolphin')

    def test_component_groups(self):
        self.assertEqual(len(self.entity.component_groups), 7)
        group = self.entity.get_component_group('dolphin_adult')
        self.assertEqual(group.id, 'dolphin_adult')
        self.assertEqual(len(group.components), 4)

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
        
        # Test deleting a path which does not exist
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

        # Test works if path does not exist
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