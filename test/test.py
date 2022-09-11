import unittest
import sys
import functools
import shutil
from typing import Union, Tuple

sys.path.insert(0, '../reticulator')
from reticulator import *

def get_packs() -> Tuple[BehaviorPack, ResourcePack]:
    project = Project('./content/bp/', './content/rp/')
    project.set_output_directory('out')
    return project.get_packs()

def save_and_return_packs(rp: ResourcePack = None, bp: BehaviorPack = None, force: bool = False):
    # Prepare folder location
    prepare_output_directory()

    # Save the old packs
    if rp is not None:
        rp.output_directory = './out/rp/'
        rp.save(force=force)
    
    if bp is not None:
        bp.output_directory = './out/bp/'
        bp.save(force=force)

    # Return the saved packs packs
    project = Project('./out/bp/', './out/rp/')
    return project.behavior_pack, project.resource_pack

def prepare_output_directory():
    try:
        shutil.rmtree('./out')
    except OSError as e:
        pass

    os.mkdir('./out')

class TestContextManager(unittest.TestCase):
    def test_context_manager(self):
        bp, rp = get_packs()

        with rp.get_entity('minecraft:dolphin') as dolphin:
            dolphin.set_jsonpath('test', 'test')

            # Dirty before save
            self.assertTrue(dolphin.dirty)

        # No longer dirty after implicit save (from context manager)
        self.assertFalse(dolphin.dirty)



class TestFogs(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_fog_files(self):
        self.assertEqual(len(self.rp.fogs), 3)
        fog_file = self.rp.get_fog('minecraft:fog_mushroom_island_shore')
        self.assertEqual(len(fog_file.distance_components), 2)
        self.assertEqual(len(fog_file.volumetric_density_components), 1)
        self.assertEqual(len(fog_file.volumetric_media_coefficients), 2)

        component = fog_file.get_distance_component('air')
        self.assertEqual(component.data['fog_end'], 60)


class TestStandaloneTextureFiles(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()
    
    def test_terrain_texture_file(self):
        terrain_texture = self.rp.terrain_texture_file
        texture_definition = terrain_texture.texture_definitions[0]

        self.assertEqual(len(terrain_texture.texture_definitions), 5)
        self.assertEqual(texture_definition.textures[0], 'textures/blocks/planks_acacia')

        texture_definition = terrain_texture.get_texture_definition('anvil_base')

        self.assertEqual(texture_definition.textures[0], 'textures/blocks/anvil_base')
        self.assertEqual(len(texture_definition.textures), 4)


    def test_item_texture_file(self):
        item_texture_file = self.rp.item_texture_file
        texture_definition = item_texture_file.texture_definitions[0]

        self.assertEqual(len(item_texture_file.texture_definitions), 5)
        self.assertEqual(texture_definition.textures[0], 'textures/items/apple')
    
        texture_definition = item_texture_file.get_texture_definition('axe')

        self.assertEqual(texture_definition.textures[0], 'textures/items/wood_axe')
        self.assertEqual(len(texture_definition.textures), 6)

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
        self.item_texture_file = self.rp.item_texture_file
        self.texture_definition = self.item_texture_file.get_texture_definition('axe')

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
    def test_property(self):
        self.entity.identifier = 'bob'

    @assert_dirties('entity')
    def test_jsonpath(self):
        self.entity.set_jsonpath('new_key', {})

    @assert_dirties('component')
    @assert_dirties('entity')
    def test_subresource(self):
        self.component.set_jsonpath('new_key', "")

    @assert_dirties('component')
    @assert_dirties('entity')
    def test_subresource_id(self):
        self.component.id = 'new_component_name'

    @assert_dirties('item_texture_file')
    @assert_dirties('texture_definition')
    def test_texture_definition(self):
        self.texture_definition.shortname = 'new_shortname'

    @assert_dirties('item_texture_file')
    @assert_dirties('texture_definition')
    def test_texture_definition_textures(self):
        self.texture_definition.textures.append('new_texture')

    @assert_dirties('item_texture_file')
    def test_add(self):
        self.item_texture_file.add_texture_definition('new_definition', [])

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

class TestAnimationRP(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_animation_file(self):
        self.assertEqual(1, len(self.rp.animation_files))
        self.assertTrue(self.rp.get_animation_file('animations/dolphin.animation.json'))

        animation_file = self.rp.get_animation_file('animations/dolphin.animation.json')
        
        self.assertEqual(1, len(animation_file.animations))
        self.assertTrue(animation_file.get_animation('animation.dolphin.move'))





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
        saved_bp, saved_rp = save_and_return_packs(rp=self.rp)

        animation = saved_rp.get_entity('minecraft:dolphin').animations[0]

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
        group = self.entity.get_component_group('dolphin_adult')

        self.assertEqual(len(self.entity.component_groups), 7)
        self.assertEqual(group.id, 'dolphin_adult')
        self.assertEqual(len(group.components), 4)

    def test_add_component_groups(self):
        # Test adding component group by name and data
        component_group_data = { "minecraft:damage" : { "value" : 1 } }
        component_group = self.entity.add_component_group('group:one',component_group_data)
        self.assertEqual(component_group.id, 'group:one')
        self.assertEqual(len(self.entity.component_groups), 8)

        # Test adding component group by class
        group = ComponentGroup({}, self.entity, 'minecraft:entity/component_groups/group:two')
        added_group = self.entity.add_component_group(group)
        self.assertEqual(added_group.id, 'group:two')
        self.assertEqual(len(self.entity.component_groups), 9)

        saved_bp, saved_rp = save_and_return_packs(bp=self.bp)

        saved_entity = saved_bp.get_entity('minecraft:dolphin')
        new_group = saved_entity.get_component_group('group:one')
        self.assertEqual(new_group.id, 'group:one')
        self.assertEqual(len(new_group.components), 1)

    def test_add_component(self):
        # Tests before
        self.assertEqual(len(self.entity.components), 29)

        # Add to components
        component_data = { "value" : 1 }
        self.entity.add_component("minecraft:damage", component_data)

        saved_bp, saved_rp = save_and_return_packs(bp=self.bp)

        saved_entity = saved_bp.get_entity('minecraft:dolphin')
        self.assertEqual(len(saved_entity.components), 30)
        

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

class TestDeletion(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Project('./content/bp/', './content/rp/')
        self.bp = self.project.behavior_pack
        self.rp = self.project.resource_pack

    def test_file_deletion(self):
        """
        Tests that we can delete a file.
        """

        # Delete entity
        entity = self.bp.get_entity('minecraft:dolphin')
        entity.delete()

        saved_bp, saved_rp = save_and_return_packs(bp=self.bp)

        # Check that the file is gone
        with self.assertRaises(AssetNotFoundError):
            saved_bp.get_entity('minecraft:dolphin')

    def test_subresource_deletion(self):
        # Delete entity
        entity = self.bp.get_entity('minecraft:dolphin')
        component = entity.get_component('minecraft:type_family')
        component.delete()

        saved_bp, saved_rp = save_and_return_packs(bp=self.bp)
        entity = saved_bp.get_entity('minecraft:dolphin')

        with self.assertRaises(AssetNotFoundError):
            component = entity.get_component('minecraft:type_family')
    
    def test_list_subresource_deletion(self):
        model = self.rp.get_model('geometry.dolphin')

        self.assertEqual(len(model.bones), 9)
        bone = model.get_bone('bristle2')
        bone.delete()
        self.assertEqual(len(model.bones), 9)

        # This fails, because the list can no longer be accessed
        # saved_bp, saved_rp = save_and_return_packs(rp=self.rp)

        # bone = model.get_bone('bristle2')


class TestModels(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = Project('./content/bp/', './content/rp/').get_packs()

    def test_model_file(self):
        self.assertEqual(len(self.rp.models), 1)
        self.assertTrue(len(self.rp.model_files), 1)
        
        model_file = self.rp.model_files[0]
        model = self.rp.get_model('geometry.dolphin')
        self.assertEqual(model_file.models[0].id, model.id)

        self.assertEqual(model.file.file_name, 'dolphin.geo.json')

    def test_bones(self):
        model = self.rp.get_model('geometry.dolphin')
        self.assertEqual(len(model.bones), 9)

class TestLanguageFiles(unittest.TestCase):
    def setUp(self) -> None:
        self.bp, self.rp = get_packs()

    def test_language_file(self):
        self.assertEqual(len(self.rp.language_files), 1)

        language_file = self.rp.get_language_file('texts/es_ES.lang')

        with self.assertRaises(AssetNotFoundError):
            self.rp.get_language_file('texts/dne.lang')

        self.assertEqual(len(language_file.translations), 3)
        translation = language_file.get_translation('accessibility.text.period')

        self.assertEqual(translation.key, 'accessibility.text.period')
        self.assertEqual(translation.value, 'Punto')
        self.assertEqual(translation.comment, '')

    def test_adding_translation(self):
        language_file = self.rp.get_language_file('texts/es_ES.lang')
        language_file.add_translation(Translation('new_key', 'new_value'))
        language_file.add_translation(Translation('new_key2', 'new_value2', comment="Test"))

        saved_bp, saved_rp = save_and_return_packs(rp=self.rp)

        language_file = saved_rp.get_language_file('texts/es_ES.lang')
        self.assertEqual(len(language_file.translations), 5)
        translation = language_file.get_translation('new_key2')
        self.assertEqual(translation.comment, 'Test')

    def test_overwrite_translation(self):
        language_file = self.rp.get_language_file('texts/es_ES.lang')
        language_file.add_translation(Translation('accessibility.text.period', 'Test 1'),overwrite=True)
        language_file.add_translation(Translation('accessibility.text.comma', 'Test 2'),overwrite=False)

        saved_bp, saved_rp = save_and_return_packs(rp=self.rp)

        language_file = saved_rp.get_language_file('texts/es_ES.lang')
        self.assertEqual(len(language_file.translations), 3)
        translation_1 = language_file.get_translation('accessibility.text.period')
        translation_2 = language_file.get_translation('accessibility.text.comma')
        self.assertEqual(translation_1.value,'Test 1')
        self.assertEqual(translation_2.value,'Coma')

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

        # Delete list
        path = 'minecraft:entity/events/minecraft:entity_spawned/randomize/0'

        # A complex test. Probably should be made clearer. 
        # The idea is that deleting a list from a jsonpath should set it to 
        # None, which the dpath lib apparently does by default
        self.assertEqual(len(entity.get_jsonpath('minecraft:entity/events/minecraft:entity_spawned/randomize')), 2)
        self.assertNotEqual(entity.get_jsonpath(path), None)
        entity.delete_jsonpath(path)
        self.assertEqual(entity.get_jsonpath(path), None)
        self.assertEqual(len(entity.get_jsonpath('minecraft:entity/events/minecraft:entity_spawned/randomize')), 2)

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

class TestFormatVersion(unittest.TestCase):
    """
    Tests format version getters, errors and comparison
    """

    def setUp(self) -> None:
        self.project = Project('./content/bp/', './content/rp/')
        self.bp = self.project.behavior_pack
        self.rp = self.project.resource_pack
        self.entity = self.bp.get_entity('minecraft:dolphin')
        self.recipe = self.bp.get_recipe('minecraft:acacia_boat')
        self.loot_table = self.bp.get_loot_table('loot_tables/entities/dolphin.json')

    def test_format_version(self):
        # Test getters
        self.assertEqual(self.entity.format_version, '1.16.0')
        self.assertEqual(self.recipe.format_version, '1.12.0')
        with self.assertRaises(AttributeError):
            self.loot_table.format_version

        # Test Initaliser
        self.assertEqual(FormatVersion('1'), '1.0.0.0')
        self.assertEqual(FormatVersion('12.4'), FormatVersion(FormatVersion('12.4.0.3.4')))

        # Test comparison
        self.assertTrue(self.entity.format_version > self.recipe.format_version)

        # Test setter
        self.entity.format_version = '1.17.0'
        self.assertEqual(self.entity.format_version, FormatVersion('1.17'))


        

if __name__ == '__main__':
    unittest.main()