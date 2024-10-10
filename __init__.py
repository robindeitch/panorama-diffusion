
# Panel basics : https://www.youtube.com/watch?v=0_QskeU8CPo

bl_info = {
    "name": "Panorama diffusion",
    "description": "Use Stable Diffusion to generate textures based on scene depth and project back to geo",
    "blender": (4, 1, 0),
    "category": "3D View",
    "location": "View3D > Sidebar > Pano tab",
    "warning": "Requires installation of dependencies"
}

from random import randint
import bpy
from .sdxl_client import SDXLClient

sdxl = SDXLClient()

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
        prompt = "A grassy hill on a beautiful day"
        negative_prompt = "bad quality, jpeg artifacts"
        seed = randint(1, 2147483647)
        steps = 15
        prompt_guidance=7.5
        depth_image_influence = 0.85
        lora_overall_influence = 1.0
        depth_image_file = "D:/code/diffusion-server-files/input-depth.png"

        def callback(id:int, image_file:str):
            print(f"Finished generating id {id} at {image_file}")

        id = sdxl.queue_panorama(
            "D:/code/diffusion-server-files/temp.png",
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

        layout.operator("panorama_diffusion.init", text="Load models", icon="MONKEY")
        layout.operator("panorama_diffusion.render", text="Render")


def register():
    bpy.types.Scene.pd_model_file = bpy.props.StringProperty(name="Model file")

    bpy.utils.register_class(RenderDiffusionPanoramaOp)
    bpy.utils.register_class(InitDiffusionPanoramaOp)
    bpy.utils.register_class(PanoramaDiffusionPanel)

def unregister():
    bpy.utils.unregister_class(PanoramaDiffusionPanel)
    bpy.utils.unregister_class(InitDiffusionPanoramaOp)
    bpy.utils.unregister_class(RenderDiffusionPanoramaOp)
