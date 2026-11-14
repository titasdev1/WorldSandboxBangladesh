extends RefCounted
class_name ASquareExperienceRegistry

const OPEN_WORLD_ID := "jibon_jatra"
const OPEN_WORLD_NAME := "JIBONJATRA"
const ROAD_ACTIVITY_ID := "roadline"
const ROAD_ACTIVITY_NAME := "ROADLINE"
const FOOTBALL_ID := "pitchbound"
const FOOTBALL_NAME := "PITCHBOUND"

const EXPERIENCES := {
    "jibon_jatra": {
        "display_name":"JibonJatra",
        "type":"living_open_world",
        "contains":["walking","vehicles","free_roam","deshi_missions","social_meetups","roadline","pitchbound"],
        "state":"active_world_development"
    },
    "strikefront": {
        "display_name":"Strikefront",
        "type":"combat_playlist_hub",
        "contains":["multiplayer","ranked","clash_squad","battle_royale","ranked_battle_royale","zombie","special_operations"],
        "state":"combat_modes_in_staged_development"
    },
    "pitchbound": {
        "display_name":"Pitchbound",
        "type":"stadium_activity",
        "variants":["3d_single_operator_11v11","2d_tactical_football"],
        "ai_fills_open_positions":true
    },
    "greenwake": {
        "display_name":"Greenwake: The Monsoon Relic",
        "type":"cinematic_jungle_adventure",
        "contains":["jungle","waterfalls","temples","traversal","mystery","puzzles","story_scenes"],
        "state":"planned_original_experience"
    }
}

static func get_experience(experience_id: String) -> Dictionary:
    return EXPERIENCES.get(experience_id,{})
