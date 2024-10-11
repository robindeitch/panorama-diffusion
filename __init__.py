
# Panel basics : https://www.youtube.com/watch?v=0_QskeU8CPo

bl_info = {
    "name": "Panorama diffusion",
    "description": "Use Stable Diffusion to generate textures based on scene depth and project back to geo",
    "blender": (4, 1, 0),
    "category": "3D View",
    "location": "View3D > Sidebar > Pano tab",
}

from random import randint
import bpy
import os
from .sdxl_client import SDXLClient

sdxl = SDXLClient()

def clean_path(file:str) -> str:
    return os.path.normpath(bpy.path.abspath(file))

class InitDiffusionPanoramaOp(bpy.types.Operator):
    bl_idname = "panorama_diffusion.init"
    bl_label = "panorama_diffusion.init"

    def execute(self, context):
        model_file = context.scene.pd_model_file
        print(f"Loading model {model_file}")
        sdxl.init(model_file)
        return {"FINISHED"}


class RenderDiffusionPanoramaOp(bpy.types.Operator):
    bl_idname = "panorama_diffusion.render"
    bl_label = "panorama_diffusion.render"

    def execute(self, context):

        # Setup prompt
        output_image_file = clean_path(context.scene.pd_output_texture_file)
        prompt = context.scene.pd_prompt
        negative_prompt = "bad quality, jpeg artifacts"
        seed = context.scene.pd_seed
        steps = 15
        prompt_guidance=7.5
        depth_image_influence = 0.85
        lora_overall_influence = 1.0
        depth_image_file = clean_path(context.scene.pd_depth_texture_file)

        # Render from the correct camera
        temp_cam = context.scene.camera
        context.scene.camera = context.scene.pd_render_cam
        bpy.ops.render.render(write_still = True)
        context.scene.camera = temp_cam

        # Reload depth map
        for img in bpy.data.images :
            this_image_file = clean_path(img.filepath)
            if img.source == 'FILE' and this_image_file == depth_image_file:
                img.reload()

        # Define callback
        def callback(id:int, result_image_file:str):
            
            result_image_file = clean_path(result_image_file)
            print(f"Finished generating id {id} at {result_image_file}, reloading")

            for img in bpy.data.images :
                this_image_file = clean_path(img.filepath)
                if img.source == 'FILE' and (this_image_file == result_image_file or this_image_file == depth_image_file):
                    img.reload()

        # Queue prompt
        id = sdxl.queue_panorama(
            output_image_file,
            callback,
            prompt,
            negative_prompt,
            seed,
            steps,
            prompt_guidance,
            depth_image_file,
            depth_image_influence,
            lora_overall_influence
        )
        print(f"Generating id {id}")
        
        return {"FINISHED"}


class PanoramaDiffusionPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_panorama_diffusion"
    bl_label = "Panorama Diffusion"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Pano'

    @classmethod
    def poll(cls, context):
        return (context.object is not None)

    def draw(self, context):
        layout = self.layout

        layout.prop(context.scene, "pd_model_file")
        layout.operator("panorama_diffusion.init", text="Load models", icon="LIBRARY_DATA_DIRECT")

        layout.prop(context.scene, "pd_prompt")
        layout.prop(context.scene, "pd_depth_texture_file")
        layout.prop(context.scene, "pd_output_texture_file")
        layout.prop(context.scene, "pd_render_cam")
        layout.prop(context.scene, "pd_seed")
        layout.operator("panorama_diffusion.render", text="Render", icon="RENDER_RESULT")

# https://docs.blender.org/api/current/bpy.props.html
# https://wilkinson.graphics/blender-icons/

def register():
    sdxl.start()
    bpy.types.Scene.pd_seed = bpy.props.IntProperty(name="Seed")
    bpy.types.Scene.pd_prompt = bpy.props.StringProperty(name="Prompt")
    bpy.types.Scene.pd_model_file = bpy.props.StringProperty(subtype="FILE_PATH", name="Model file")
    bpy.types.Scene.pd_depth_texture_file  = bpy.props.StringProperty(subtype="FILE_PATH", name="Depth texture file")
    bpy.types.Scene.pd_output_texture_file  = bpy.props.StringProperty(subtype="FILE_PATH", name="Output texture file")
    bpy.types.Scene.pd_render_cam = bpy.props.PointerProperty(type=bpy.types.Object)

    bpy.utils.register_class(RenderDiffusionPanoramaOp)
    bpy.utils.register_class(InitDiffusionPanoramaOp)
    bpy.utils.register_class(PanoramaDiffusionPanel)

def unregister():
    sdxl.stop()
    bpy.utils.unregister_class(PanoramaDiffusionPanel)
    bpy.utils.unregister_class(InitDiffusionPanoramaOp)
    bpy.utils.unregister_class(RenderDiffusionPanoramaOp)
