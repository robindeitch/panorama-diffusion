bl_info = {
    "name": "Panorama diffusion",
    "description": "Use Stable Diffusion to generate textures based on scene depth and project back to geo",
    "blender": (4, 1, 0),
    "category": "Panel",
}

import bpy

class RunDiffusionPanoramaOp(bpy.types.Operator):
    '''Test tooltip'''
    bl_idname = "panorama_diffusion.run"
    bl_label = "Test instructions"

    def execute(self, context):
        print("HELLO")
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

        row = layout.row()
        row.operator("panorama_diffusion.run", text="Run pano diff")


def register():
    bpy.utils.register_class(RunDiffusionPanoramaOp)
    bpy.utils.register_class(PanoramaDiffusionPanel)

def unregister():
    bpy.utils.unregister_class(PanoramaDiffusionPanel)
    bpy.utils.unregister_class(RunDiffusionPanoramaOp)