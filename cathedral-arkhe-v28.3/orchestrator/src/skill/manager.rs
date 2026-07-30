use std::collections::HashMap;

#[derive(Debug, Clone)]
pub enum SkillType {
    UserInvoked,
    ModelInvoked,
    Background,
}

#[derive(Debug, Clone)]
pub struct Skill {
    pub name: String,
    pub description: String,
    pub skill_type: SkillType,
    pub version: String,
    pub tags: Vec<String>,
    pub triggers: Vec<String>,
    pub author: Option<String>,
}

impl Skill {
    pub fn new(name: &str, description: &str, skill_type: SkillType) -> Self {
        Self {
            name: name.to_string(),
            description: description.to_string(),
            skill_type,
            version: "1.0.0".to_string(),
            tags: Vec::new(),
            triggers: Vec::new(),
            author: None,
        }
    }
}

pub struct SkillManager {
    pub skills: HashMap<String, Skill>,
}

impl SkillManager {
    pub fn new() -> Self {
        Self {
            skills: HashMap::new(),
        }
    }

    pub fn load_skill(&mut self, skill: Skill) {
        self.skills.insert(skill.name.clone(), skill);
    }

    pub fn export_as_ard_catalog(&self) -> String {
        let mut catalog = serde_json::json!({
            "version": "1.0",
            "capabilities": []
        });

        if let Some(capabilities) = catalog.get_mut("capabilities").and_then(|c| c.as_array_mut()) {
            for skill in self.skills.values() {
                capabilities.push(serde_json::json!({
                    "id": skill.name,
                    "name": skill.name,
                    "description": skill.description,
                    "type": format!("{:?}", skill.skill_type),
                    "version": skill.version,
                    "tags": skill.tags,
                    "triggers": skill.triggers,
                    "author": skill.author,
                }));
            }
        }

        serde_json::to_string_pretty(&catalog).unwrap_or_else(|_| "{}".to_string())
    }
}
