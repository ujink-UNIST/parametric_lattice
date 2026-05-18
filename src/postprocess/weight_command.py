from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_node_volume_mass_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute lumped nodal volume and mass by distributing element volume.

    Output MAPDL parameters:
      - pp_node_vol:  ARRAY(nmax) indexed by node id
      - pp_node_mass: ARRAY(nmax) indexed by node id

    Mass is computed as rho * volume using the case material density.

    Assumptions:
      - Single material density is appropriate for all selected elements.
      - Element volume is available as ETABLE item VOLU.
    """

    rho = float(ctx.sim_case.post_mesh_spec.material.density)

    cmd: list[str] = [
        apdl_command("/POST1", "postprocess: node vol/mass (from element VOLU)"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL"),
        apdl_command("ESEL,ALL"),
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("*GET,pp_node_vol_nmax,NODE,0,NUM,MAX", "max node id"),
        apdl_command("*DIM,pp_node_vol,ARRAY,pp_node_vol_nmax", "nodal lumped volume"),
        apdl_command("*DIM,pp_node_mass,ARRAY,pp_node_vol_nmax", "nodal lumped mass"),
        apdl_command("*VFILL,pp_node_vol(1),RAMP,0,0", "init 0"),
        apdl_command("*VFILL,pp_node_mass(1),RAMP,0,0", "init 0"),
        apdl_command(f"pp__rho={rho:.16g}", "material density"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU", "element volume"),
        apdl_command("  *GET,pp__nen,ELEM,pp__eid,ATTR,NNOD", "# nodes in element"),
        apdl_command("  pp__vshare=pp__evol/pp__nen", "volume share per node"),
        apdl_command("  pp__mshare=pp__rho*pp__vshare", "mass share per node"),
        apdl_command("  *DO,pp__k,1,pp__nen"),
        apdl_command("    *GET,pp__nid,ELEM,pp__eid,NODE,pp__k"),
        apdl_command("    pp_node_vol(pp__nid)=pp_node_vol(pp__nid)+pp__vshare"),
        apdl_command("    pp_node_mass(pp__nid)=pp_node_mass(pp__nid)+pp__mshare"),
        apdl_command("  *ENDDO"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)
