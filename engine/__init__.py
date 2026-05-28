from .registry import get_capabilities, execute_capability, get_registry
from .skills import BaseCLI, SkillLoader, SkillInfo

__all__ = [
    'get_capabilities', 
    'execute_capability',
    'get_registry',
    'BaseCLI',
    'SkillLoader',
    'SkillInfo',
    'load_optional_tools'
]


def load_optional_tools():
    registry = get_registry()
    loaded_tools = []
    
    try:
        from .tool.browser import create_skill as create_browser_skill
        browser_skill = create_browser_skill()
        if browser_skill.check_requirements():
            registry.register_cli(browser_skill)
            loaded_tools.append("browser")
    except ImportError as e:
        pass
    
    try:
        from .tool.browser_agent_cli import create_skill as create_browser_agent_skill
        browser_agent_skill = create_browser_agent_skill()
        if browser_agent_skill.check_requirements():
            registry.register_cli(browser_agent_skill)
            loaded_tools.append("browser_agent")
    except ImportError as e:
        pass
    
    try:
        from .tool.ocr import create_skill as create_ocr_skill
        ocr_skill = create_ocr_skill()
        if ocr_skill.check_requirements():
            registry.register_cli(ocr_skill)
            loaded_tools.append("ocr")
    except ImportError as e:
        pass
    
    return loaded_tools
