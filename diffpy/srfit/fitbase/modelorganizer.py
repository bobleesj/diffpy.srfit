#!/usr/bin/env python
########################################################################
#
# diffpy.srfit      by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2008 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Chris Farrow
#
# See AUTHORS.txt for a list of people who contributed.
# See LICENSE.txt for license information.
#
########################################################################
"""The ModelOrganizer class."""

from numpy import inf

from .constraint import Constraint
from .restraint import Restraint

from diffpy.srfit.equation.builder import EquationFactory
from diffpy.srfit.equation import Equation


class ModelOrganizer(object):
    """A mixin base class for organizing pieces of a FitModel.

    FitModels are hierarchical, where Parameters, Constraints and Restraints
    can exist at each level. This mixin class provides attributes and members
    that help organize these objects at any level of the hierarcy.

    Attributes
    suborganizers   --  A list of organizers that this ModelOrganizer knows
                        about.
    constraints     --  A dictionary of Constraints, indexed by the constrained
                        Parameter. Constraints can be added using the
                        'constrain' method.
    restraints      --  A set of Restraints. Restraints can be added using the
                        'restrain' method.
    _eqfactory      --  A diffpy.srfit.equation.builder.EquationFactory
                        instance that is used to create constraints and
                        restraints from string

    """

    def __init__(self):
        self.suborganizers = []
        self.constraints = {}
        self.restraints = set()
        self._eqfactory = EquationFactory()
        return

    def constrain(self, par, eqstr, ns = {}):
        """Constrain a parameter to an equation.

        Note that only one constraint can exist on a Parameter at a time. The
        most recent constraint override all other user-defined constraints.
        Built-in constraints override all other constraints.

        par     --  The Parameter to constrain. It does not need to be a
                    variable.
        eqstr   --  A string representation of the constraint equation. The
                    constraint equation must consist of numpy operators and
                    "known" Parameters. Parameters are known if they are in the
                    ns argument, or if they have been added to the _eqfactory.
        ns      --  A dictionary of Parameters, indexed by name, that are used
                    in the eqstr, but not part of the ModelOrganizer (default
                    {}).

        Raises ValueError if ns uses a name that is already used for a
        variable.
        Raises ValueError if eqstr depends on a Parameter that is not part of
        the ModelOrganizer and that is not defined in ns.

        """

        eq = equationFromString(eqstr, self._eqfactory, ns)

        # Make and store the constraint
        con = Constraint()
        con.constrain(par, eq)
        self.constraints[par] = con

        return

    def unconstrain(self, par):
        """Unconstrain a parameter.

        par     --  The Parameter to unconstrain.

        This removes any constraints on a parameter, including built-in
        constraints.
        """
        if par in self.constraints:
            del self.constraints[par]
        return

    def restrain(self, res, lb = -inf, ub = inf, prefactor = 1, power = 2,  
            scaled = False, ns = {}):
        """Restrain an expression to specified bounds

        res     --  An equation string or Parameter to restrain.
        lb      --  The lower bound on the restraint evaluation (default -inf).
        ub      --  The lower bound on the restraint evaluation (default inf).
        prefactor   --  A multiplicative prefactor for the restraint 
                        (default 1).
        power   --  The power of the penalty (default 2).
        scaled  --  A flag indicating if the restraint is scaled (multiplied)
                    by the unrestrained point-average chi^2 (chi^2/numpoints)
                    (default False).
        ns      --  A dictionary of Parameters, indexed by name, that are used
                    in the eqstr, but not part of the ModelOrganizer (default {}).

        The penalty is calculated as 
        prefactor * max(0, lb - val, val - ub) ** power
        and val is the value of the calculated equation. This is multipled by
        the average chi^2 if scaled is True.

        Raises ValueError if ns uses a name that is already used for a
        variable.
        Raises ValueError if eqstr depends on a Parameter that is not part of
        the ModelOrganizer and that is not defined in ns.

        Returns the Restraint selfect for use with the 'unrestrain' method.

        """

        if isinstance(res, str):
            eq = equationFromString(res, self._eqfactory, ns)
        else:
            eq = Equation(root = res)

        # Make and store the constraint
        res = Restraint()
        res.restrain(eq, lb, ub, prefactor, power)
        self.restraints.add(res)

        return res

    def unrestrain(self, res):
        """Remove a restraint from the ModelOrganizer.
        
        res     --  A Restraint selfect returned from the 'restrain' method.
        """
        if res in self.restraints:
            self.restraints.remove(res)

        return

    def getConstraints(self):
        """Get the Constraints for this and embedded ParameterSets."""
        constraints = dict(self.constraints)
        for org in self.suborganizers:
            constraints.update( org.getConstraints() )

        return constraints

    def getRestraints(self):
        """Get the Restraints for this and embedded ParameterSets."""
        restraints = set(self.restraints)
        for org in self.suborganizers:
            restraints.update( org.getRestraints() )

        return restraints

# End ModelOrganizer

def equationFromString(eqstr, factory, ns = {}):
    """Make an equation from a string.

    eqstr   --  A string representation of the equation. The
                equation must consist of numpy operators and
                "known" Parameters. Parameters are known if they are in 
                ns, or already defined in the factory.
    factory --  An EquationFactory instance.
    ns      --  A dictionary of Parameters indexed by name that are used
                in the eqstr but not already defined in the factory 
                (default {}).

    Raises ValueError if ns uses a name that is already defined in the factory.
    Raises ValueError if the equation has undefined parameters.

    """

    defined = set(factory.builders.keys())

    # Check if ns overloads any variables.
    if defined.intersection(ns.keys()):
        raise ValueError("ns contains defined names")

    # Register the ns parameters in the equation factory
    for name, arg in ns.items():
        factory.registerArgument(name, arg)

    eq = factory.makeEquation(eqstr, buildargs = False)

    # Clean the ns parameters
    for name in ns:
        factory.deRegisterBuilder(name)

    return eq

