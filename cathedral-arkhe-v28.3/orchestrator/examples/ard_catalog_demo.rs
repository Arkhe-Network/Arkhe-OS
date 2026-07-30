use orchestrator::skill::manager::{SkillManager, Skill, SkillType};

fn main() {
    let mut skill_mgr = SkillManager::new();

    let mut grill_me = Skill::new(
        "grill-me",
        "Get relentlessly grilled about a plan until every decision branch is resolved",
        SkillType::UserInvoked
    );
    grill_me.author = Some("mattpocock".to_string());
    grill_me.tags = vec!["alignment".to_string(), "planning".to_string()];
    grill_me.triggers = vec!["grill".to_string(), "plan".to_string(), "align".to_string()];
    skill_mgr.load_skill(grill_me);

    let mut to_prd = Skill::new(
        "to-prd",
        "Turn conversation context into a structured PRD",
        SkillType::UserInvoked
    );
    to_prd.author = Some("mattpocock".to_string());
    to_prd.tags = vec!["product".to_string(), "documentation".to_string()];
    to_prd.triggers = vec!["prd".to_string(), "spec".to_string(), "product".to_string()];
    skill_mgr.load_skill(to_prd);

    let mut diagnose = Skill::new(
        "diagnose",
        "Disciplined diagnosis loop: reproduce -> minimise -> hypothesise -> instrument -> fix -> regression-test",
        SkillType::UserInvoked
    );
    diagnose.author = Some("mattpocock".to_string());
    diagnose.tags = vec!["debug".to_string(), "engineering".to_string()];
    diagnose.triggers = vec!["diagnose".to_string(), "debug".to_string(), "fix".to_string()];
    skill_mgr.load_skill(diagnose);

    let mut tdd = Skill::new(
        "tdd",
        "Test-Driven Development loop: red -> green -> refactor",
        SkillType::ModelInvoked
    );
    tdd.author = Some("mattpocock".to_string());
    tdd.tags = vec!["testing".to_string(), "engineering".to_string()];
    tdd.triggers = vec!["test".to_string(), "tdd".to_string(), "red-green-refactor".to_string()];
    skill_mgr.load_skill(tdd);

    let mut improve_arch = Skill::new(
        "improve-codebase-architecture",
        "Regularly rescue codebases from accelerating entropy",
        SkillType::Background
    );
    improve_arch.author = Some("mattpocock".to_string());
    improve_arch.tags = vec!["architecture".to_string(), "refactoring".to_string()];
    improve_arch.triggers = vec!["architecture".to_string(), "refactor".to_string(), "rescue".to_string()];
    skill_mgr.load_skill(improve_arch);

    let mut triage = Skill::new(
        "triage",
        "Triage issues through a state machine of triage roles",
        SkillType::UserInvoked
    );
    triage.author = Some("mattpocock".to_string());
    triage.tags = vec!["product".to_string(), "management".to_string()];
    triage.triggers = vec!["triage".to_string(), "issue".to_string()];
    skill_mgr.load_skill(triage);

    let json_catalog = skill_mgr.export_as_ard_catalog();

    println!("Generated ARD Catalog ai-catalog.json for Built-in Skills:\n");
    println!("{}", json_catalog);

    std::fs::write("ai-catalog.json", json_catalog).unwrap();
}
