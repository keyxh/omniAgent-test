"""
Skills 扩展系统 - 基础框架

提供标准接口，让开发者轻松添加新技能
"""

from dataclasses import dataclass, field
from typing import Dict, Callable, Optional, List, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillInfo:
    handler: Callable
    description: str
    parameters: Dict
    category: str = "general"
    requires: List[str] = field(default_factory=list)


class BaseCLI:
    """
    CLI 技能基类
    
    所有自定义技能都应该继承这个类
    """
    
    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, SkillInfo] = {}
    
    def register_skill(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Dict,
        category: str = "general",
        requires: Optional[List[str]] = None
    ):
        self.tools[name] = SkillInfo(
            handler=handler,
            description=description,
            parameters=parameters,
            category=category,
            requires=requires or []
        )
        logger.info(f"注册技能: {self.name}.{name}")
    
    def check_requirements(self) -> bool:
        """检查依赖是否满足"""
        return True


class SkillLoader:
    """技能加载器 - 自动发现和加载技能"""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.loaded_skills: Dict[str, BaseCLI] = {}
    
    def discover_skills(self) -> List[str]:
        """发现所有可用技能"""
        if not self.skills_dir.exists():
            return []
        
        skills = []
        for file in self.skills_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            skills.append(file.stem)
        
        return skills
    
    def load_skill(self, skill_name: str) -> Optional[BaseCLI]:
        """加载单个技能"""
        try:
            import importlib.util
            
            skill_file = self.skills_dir / f"{skill_name}.py"
            if not skill_file.exists():
                logger.warning(f"技能文件不存在: {skill_file}")
                return None
            
            spec = importlib.util.spec_from_file_location(skill_name, skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'create_skill'):
                skill = module.create_skill()
                if isinstance(skill, BaseCLI):
                    self.loaded_skills[skill_name] = skill
                    logger.info(f"加载技能成功: {skill_name}")
                    return skill
            
            logger.warning(f"技能模块缺少 create_skill 函数: {skill_name}")
            return None
            
        except Exception as e:
            logger.error(f"加载技能失败 {skill_name}: {e}", exc_info=True)
            return None
    
    def load_all_skills(self) -> List[BaseCLI]:
        """加载所有技能"""
        skills = self.discover_skills()
        loaded = []
        
        for skill_name in skills:
            skill = self.load_skill(skill_name)
            if skill:
                loaded.append(skill)
        
        logger.info(f"共加载 {len(loaded)} 个技能")
        return loaded
    
    def get_skill(self, name: str) -> Optional[BaseCLI]:
        """获取已加载的技能"""
        return self.loaded_skills.get(name)


def register_skills_to_registry(skills: List[BaseCLI], registry):
    """将技能注册到全局注册表"""
    for skill in skills:
        registry.register_cli(skill)
        logger.info(f"技能 {skill.name} 已注册到全局注册表")
