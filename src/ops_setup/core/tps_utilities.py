"""
TPS utility mixin providing common functionality for TPS setups.

This mixin provides reusable methods for selector creation, move scheme setup,
etc. that can be used by different TPS setup classes regardless of their
initialization pattern.
"""

from typing import Optional
import openpathsampling as paths


class TPSUtilitiesMixin:
    """
    Mixin providing common TPS utilities.
    
    This class can be mixed into any TPS setup class to provide standard
    selector and move scheme creation methods. It expects the class to have:
    - self.config (dict): Configuration dictionary
    - self.md_engine or self.engine: OpenPathSampling engine
    
    Methods
    -------
    _create_selector : Create shooting point selector
    _create_velocity_modifier : Create velocity randomizer
    create_move_scheme : Create move scheme for path sampling
    """
    
    def _create_selector(self, selector_type=None, collective_variable=None, collective_variable_name=None, **kwargs):
        """
        Create a shooting point selector.

        Parameters
        ----------
        selector_type : str, optional
            Type of selector ('uniform', 'gaussian'). If None, uses config value.
        collective_variable : CollectiveVariable, optional
            CV for gaussian selector. If None, looks up by collective_variable_name.
        collective_variable_name : str, optional
            Name of CV to look up (e.g., 'mouth_distance', 'p_value').
            Looks for self.<name>_cv attribute. If None, uses config value.
        **kwargs : dict
            Additional parameters:
            - width: float, gaussian width parameter
            - origin_shift: float, gaussian origin shift

        Returns
        -------
        ShootingPointSelector
            Selector for choosing shooting points.
        """
        # Get selector type from config if not specified
        if selector_type is None:
            tps_settings = getattr(self, 'config', {}).get('TPS_settings', {})
            selector_type = tps_settings.get('selector', 'uniform')
        
        selector_type = selector_type.lower()
        
        if selector_type == 'uniform':
            return paths.UniformSelector()
        
        if selector_type == 'gaussian':
            gaussian_cls = getattr(paths, 'GaussianBiasSelector', None)
            if gaussian_cls is None:
                raise ValueError(
                    "Gaussian selector requested but paths.GaussianBiasSelector unavailable"
                )
            
            # Get CV if not provided
            if collective_variable is None:
                # Try to get CV name from config
                if collective_variable_name is None:
                    tps_settings = getattr(self, 'config', {}).get('TPS_settings', {})
                    collective_variable_name = tps_settings.get('selector_cv')
                
                # Look up CV by name from self
                if collective_variable_name:
                    cv_attr = f"{collective_variable_name}_cv"
                    if hasattr(self, cv_attr):
                        collective_variable = getattr(self, cv_attr)
                    else:
                        raise ValueError(
                            f"CV '{collective_variable_name}' not found. "
                            f"Available: {[a for a in dir(self) if a.endswith('_cv')]}"
                        )
                else:
                    raise ValueError(
                        "No CV specified for GaussianBiasSelector. "
                        "Provide either collective_variable parameter, "
                        "collective_variable_name parameter, or "
                        "'selector_cv' in TPS_settings config."
                    )
            
            # Get params from kwargs or config
            tps_settings = getattr(self, 'config', {}).get('TPS_settings', {})
            selector_params = tps_settings.get('selector_parameters', {})
            
            width = kwargs.get('width', selector_params.get('width', 0.1))
            origin_shift = kwargs.get('origin_shift', selector_params.get('origin_shift', 0.0))
            
            return gaussian_cls(
                collective_variable,
                alpha=1/(2*width**2),
                l_0=origin_shift
            )
        
        raise ValueError(f"Unknown selector type '{selector_type}'")
    
    def _create_velocity_modifier(self):
        """
        Create a velocity randomizer for two-way shooting.

        Returns
        -------
        RandomVelocities or None
            Modifier to randomize velocities, or None if beta unavailable.
        """
        # Get engine
        engine = getattr(self, 'engine', None) or getattr(self, 'md_engine', None)
        if engine is None:
            return None
        
        # Get integrator
        integrator = getattr(engine, 'integrator', None)
        if integrator is None:
            return None
        
        # Try to get beta
        beta = getattr(integrator, 'beta', None)

        if beta is None and hasattr(integrator, 'getTemperature'):
            try:
                from openmm import unit as openmm_unit
            except ImportError:
                try:
                    from simtk import unit as openmm_unit
                except ImportError:
                    openmm_unit = None

            if openmm_unit is not None:
                temp = integrator.getTemperature()
                beta = 1.0 / (temp * openmm_unit.BOLTZMANN_CONSTANT_kB)

        if beta is None:
            return None

        return paths.RandomVelocities(beta=beta, engine=engine)
    
    def create_move_scheme(self, network, scheme_type=None, selector=None):
        """
        Create a move scheme for path sampling.
        
        All TPS settings come from config:
        - TPS_settings.shooting_scheme: 'OneWay' or 'TwoWay'
        - TPS_settings.selector: 'uniform' or 'gaussian'
        - TPS_settings.selector_cv: CV name for gaussian selector (e.g., 'mouth_distance')
        - TPS_settings.selector_parameters: width, origin_shift
        
        Parameters
        ----------
        network : Network
            The path sampling network.
        scheme_type : str, optional
            Type of shooting scheme ('OneWay' or 'TwoWay').
            If None, uses TPS_settings.shooting_scheme from config.
        selector : ShootingPointSelector, optional
            Custom selector. If None, creates one based on config
            (selector type, CV name, parameters all from TPS_settings).
            
        Returns
        -------
        MoveScheme
            OpenPathSampling move scheme.
        """
        # Get engine
        engine = getattr(self, 'engine', None) or getattr(self, 'md_engine', None)
        if engine is None:
            raise ValueError("No engine found (need self.engine or self.md_engine)")
        
        # Get scheme type from config if not specified
        if scheme_type is None:
            tps_settings = getattr(self, 'config', {}).get('TPS_settings', {})
            scheme_type = tps_settings.get('shooting_scheme', 'OneWay')
        
        # Create selector if not provided
        if selector is None:
            selector = self._create_selector()

        if scheme_type == "OneWay":
            return paths.OneWayShootingMoveScheme(
                network,
                selector=selector,
                engine=engine
            )

        if scheme_type == "TwoWay":
            modifier = self._create_velocity_modifier()
            tw_strategy = paths.strategies.TwoWayShootingStrategy(
                modifier=modifier,
                selector=selector,
                engine=engine,
                group="TwoWayShooting"
            )

            move_scheme = paths.MoveScheme(network=network)
            move_scheme.append(tw_strategy)
            move_scheme.append(paths.strategies.OrganizeByMoveGroupStrategy())
            move_scheme.build_move_decision_tree()
            return move_scheme

        raise ValueError(f"Scheme type '{scheme_type}' not recognized")
