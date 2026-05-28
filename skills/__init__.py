"""
Skills 初始化文件

自动加载所有技能
"""

from pathlib import Path
import logging

from engine.skills import SkillLoader, register_skills_to_registry
from engine.registry import get_registry

logger = logging.getLogger(__name__)


def load_all_skills():
    """加载所有技能到全局注册表"""
    skills_dir = Path(__file__).parent
    loader = SkillLoader(skills_dir)
    
    skills = loader.load_all_skills()
    
    registry = get_registry()
    register_skills_to_registry(skills, registry)
    
    logger.info(f"技能系统初始化完成，共加载 {len(skills)} 个技能")
    
    return skills


__all__ = ['load_all_skills']
