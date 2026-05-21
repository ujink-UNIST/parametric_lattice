from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_element_strain_energy_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Extract *per-element* strain energy.

    Output MAPDL parameters:
      - pp_elem_sene: ARRAY(emax)
          Indexed by element number (EID). For non-existent EIDs the value will
          remain 0.
      - pp_elem_sene_emax: scalar (max element number, i.e. len(pp_elem_sene))

    Notes:
      - Intended as an intermediate result (not written to Excel).
      - Requires element strain energy to be available in POST1 as ETABLE item
        SENE.
      - Uses the currently selected result SET (we follow the repo convention
        and do SET,LAST here, like the stress/volume blocks).
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("/POST1", "postprocess: element strain energy (SENE)"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL"),
        apdl_command("ESEL,ALL"),
        apdl_command("ETABLE,pp__SENE,SENE", "element strain energy"),
        apdl_command("*GET,pp_elem_sene_emax,ELEM,0,NUM,MAX", "max element id"),
        apdl_command("*DIM,pp_elem_sene,ARRAY,pp_elem_sene_emax", "element energy by element id"),
        apdl_command("*VFILL,pp_elem_sene(1),RAMP,0,0", "initialize to 0"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__esene,ELEM,pp__eid,ETAB,pp__SENE", "element SENE"),
        apdl_command("  pp_elem_sene(pp__eid)=pp__esene"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH", "next element"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def build_node_strain_energy_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Extract *per-node* strain energy aggregated from *element* strain energy.

    Output MAPDL parameters:
      - pp_node_sene: ARRAY(nmax)
          Indexed by node number. Value is the sum over connected elements of
          (element_strain_energy / nnode_in_element).
      - pp_node_sene_nmax: scalar (max node number, i.e. len(pp_node_sene))

    Notes:
      - This is intended as an intermediate result (not written to Excel).
      - Requires that element strain energy is available in POST1 as ETABLE item
        SENE.
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("/POST1", "postprocess: node strain energy (from element SENE)"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL"),
        apdl_command("ESEL,ALL"),
        apdl_command("ETABLE,pp__SENE,SENE", "element strain energy"),
        apdl_command("*GET,pp_node_sene_nmax,NODE,0,NUM,MAX", "max node id"),
        apdl_command("*DIM,pp_node_sene,ARRAY,pp_node_sene_nmax", "node energy by node id"),
        apdl_command("*VFILL,pp_node_sene(1),RAMP,0,0", "initialize to 0"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__esene,ELEM,pp__eid,ETAB,pp__SENE", "element SENE"),
        apdl_command("  *GET,pp__nen,ELEM,pp__eid,ATTR,NNOD", "# nodes in element"),
        apdl_command("  pp__share=pp__esene/pp__nen", "energy share per node"),
        apdl_command("  *DO,pp__k,1,pp__nen"),
        apdl_command("    *GET,pp__nid,ELEM,pp__eid,NODE,pp__k", "k-th node of element"),
        apdl_command("    pp_node_sene(pp__nid)=pp_node_sene(pp__nid)+pp__share"),
        apdl_command("  *ENDDO"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH", "next element"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)
