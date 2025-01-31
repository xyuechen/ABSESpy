#!/usr/bin/env python 3.11.0
# -*-coding:utf-8 -*-
# @Author  : Shuang (Twist) Song
# @Contact   : SongshGeo@gmail.com
# GitHub   : https://github.com/SongshGeo
# Website: https://cv.songshgeo.com/

"""
每一个世界里的斑块
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union

from mesa_geo.raster_layers import RasterBase
from pyproj import CRS

from abses._bases.errors import ABSESpyError
from abses._bases.objects import _BaseObj
from abses.container import _CellAgentsContainer
from abses.links import TargetName, _LinkNodeCell

if TYPE_CHECKING:
    from abses.nature import PatchModule
    from abses.sequences import ActorsList

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias

Pos: TypeAlias = Tuple[int, int]


def raster_attribute(
    func: Callable[[Any], Union[str | int | float]]
) -> property:
    """Turn the method into a property that the patch can extract.
    Example:
        ```
        class TestCell(Cell):
            @raster_attribute
            def test:
                return 1

        # Using this test cell to create a PatchModule.
        module = PatchModule.from_resolution(
            model=MainModel(),
            shape=(3, 3),
            cell_cls=TestCell,
        )

        # now, the attribute 'test' of TestCell can be accessible in the module, as spatial data (i.e., raster layer).

        >>> module.cell_properties
        >>> set('test')

        >>> array = module.get_raster('test')
        >>> np.array([
            [1, 1, 1],
            [1, 1, 1],
            [1, 1, 1],
        ])
        ```
    """
    setattr(func, "is_decorated", True)
    return property(func)


class PatchCell(_LinkNodeCell, _BaseObj):
    """A patch cell of a `RasterLayer`.
    Subclassing this class to create a custom cell.
    When class attribute `max_agents` is assigned,
    the `agents` property will be limited to the number of agents.

    Attributes:
        agents:
            The agents located at here.
        layer:
            The `RasterLayer` where this `PatchCell` belongs.
    """

    max_agents: Optional[int] = None

    def __init__(
        self,
        layer: PatchModule,
        indices: Pos,
        pos: Optional[Pos] = None,
    ):
        _BaseObj.__init__(self, model=layer.model, observer=True)
        _LinkNodeCell.__init__(self)
        self.indices = indices
        self.pos = pos
        self._set_layer(layer=layer)

    def __repr__(self) -> str:
        return f"<Cell at {self.layer}[{self.indices}]>"

    @classmethod
    def __attribute_properties__(cls) -> set[str]:
        """Properties that should be found in the `RasterLayer`.

        Users should decorate a property attribute when subclassing `PatchCell` to make it accessible in the `RasterLayer`.
        """
        return {
            name
            for name, method in cls.__dict__.items()
            if isinstance(method, property)
            and getattr(method.fget, "is_decorated", False)
        }

    @property
    def layer(self) -> PatchModule:
        """`RasterLayer` where this `PatchCell` belongs."""
        if self._layer is None:
            raise ABSESpyError(
                "PatchCell must belong to a layer."
                f"However, {self} has no layer."
                "Did you create this cell in the correct way?"
            )
        return self._layer

    @property
    def agents(self) -> _CellAgentsContainer:
        """The agents located at here."""
        return self._agents

    @property
    def coordinate(self) -> Tuple[float, float]:
        """The position of this cell."""
        row, col = self.indices
        return self.layer.transform_coord(row=row, col=col)

    @property
    def geo_type(self) -> str:
        """Return the geo_type"""
        # TODO: 返回地理类型，可以是 Geometry 或 Raster
        return "Cell"

    @property
    def crs(self) -> Optional[CRS]:
        """The crs of this cell, the same as the layer."""
        return self.layer.crs

    def _set_layer(self, layer: PatchModule) -> None:
        if not isinstance(layer, RasterBase):
            raise TypeError(f"{type(layer)} is not valid layer.")
        # set layer property
        self._layer = layer
        # set agents container
        self._agents = _CellAgentsContainer(
            layer.model, cell=self, max_len=getattr(self, "max_agents", None)
        )

    def get(
        self,
        attr: str,
        target: Optional[TargetName] = None,
        default: Any = None,
    ) -> Any:
        """Gets the value of an attribute or registered property.
        Automatically update the value if it is the dynamic variable of the layer.

        Parameters:
            attr: The name of attribute to get.
            target: Optional target name.
            default: Default value if attribute is not found.

        Returns:
            Any: The value of the attribute.

        Raises:
            AttributeError: Attribute value of the associated patch cell.
        """
        if attr in self.layer.dynamic_variables:
            self.layer.dynamic_var(attr_name=attr)
        return super().get(attr=attr, target=target, default=default)

    def neighboring(
        self,
        moore: bool = False,
        radius: int = 1,
        include_center: bool = False,
        annular: bool = False,
    ) -> ActorsList[PatchCell]:
        """Get the grid around the patch.

        Parameters:
            moore: Whether to include the Moore neighborhood.
            radius: The radius of the neighborhood.
            include_center: Whether to include the center cell.
            annular: Whether to use an annular neighborhood.

        Returns:
            ActorsList[PatchCell]: The neighboring cells.
        """
        return self.layer.get_neighboring_by_indices(
            self.indices,
            moore=moore,
            radius=radius,
            include_center=include_center,
            annular=annular,
        )
