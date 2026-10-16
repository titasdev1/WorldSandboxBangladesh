extends SceneTree
## Packages a complete map directory or a delta directory into a runtime-mountable PCK.
## A delta directory must contain the complete updated map_tiles_manifest.json plus only
## the new/replacement tile files. Older resources remain available from earlier packs.

const TARGET_ROOT := "assets/world/dhaka_tiles/"

func _initialize() -> void:
    var args := OS.get_cmdline_user_args()
    var source_arg := ""
    var output_arg := ""
    var i := 0
    while i < args.size():
        if args[i] == "--source" and i + 1 < args.size():
            source_arg = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < args.size():
            output_arg = args[i + 1]
            i += 2
        else:
            i += 1
    if source_arg.is_empty() or output_arg.is_empty():
        push_error("Usage: --source <map-directory> --output <output.pck>")
        quit(2)
        return

    var source_root := source_arg
    if not source_root.begins_with("res://"):
        source_root = "res://" + source_root.trim_prefix("/")
    if not DirAccess.dir_exists_absolute(ProjectSettings.globalize_path(source_root)):
        push_error("Map pack source directory does not exist: " + source_root)
        quit(2)
        return
    if not FileAccess.file_exists(source_root.path_join("map_tiles_manifest.json")):
        push_error("Map pack source must contain a complete map_tiles_manifest.json")
        quit(2)
        return

    var output_path := output_arg
    if not output_path.begins_with("res://") and not output_path.is_absolute_path():
        output_path = "res://" + output_path.trim_prefix("/")
    var output_absolute := ProjectSettings.globalize_path(output_path)
    var mkdir_error := DirAccess.make_dir_recursive_absolute(output_absolute.get_base_dir())
    if mkdir_error != OK:
        push_error("Could not create PCK output directory: " + str(mkdir_error))
        quit(1)
        return

    var packer := PCKPacker.new()
    var start_error := packer.pck_start(output_absolute)
    if start_error != OK:
        push_error("Could not start PCK output: " + str(start_error))
        quit(1)
        return
    var added := _add_directory(packer, source_root, "")
    if added <= 0:
        push_error("Map PCK contains no files.")
        quit(1)
        return
    var flush_error := packer.flush()
    if flush_error != OK:
        push_error("Could not finalize PCK: " + str(flush_error))
        quit(1)
        return
    if not ProjectSettings.load_resource_pack(output_absolute, true):
        push_error("PCK was written but could not be mounted for verification: " + output_absolute)
        quit(1)
        return
    var mounted_manifest := "res://assets/world/dhaka_tiles/map_tiles_manifest.json"
    if not FileAccess.file_exists(mounted_manifest):
        push_error("PCK verification failed; mounted map manifest is missing.")
        quit(1)
        return
    var mounted_data: Variant = JSON.parse_string(FileAccess.get_file_as_string(mounted_manifest))
    if not (mounted_data is Dictionary) or not mounted_data.has("tiles"):
        push_error("PCK verification failed; mounted map manifest is invalid.")
        quit(1)
        return
    print("MAP_PCK_VERIFIED files=", added, " bytes=", FileAccess.get_file_as_bytes(output_absolute).size(), " output=", output_absolute)
    quit(0)

func _add_directory(packer: PCKPacker, source_root: String, relative_dir: String) -> int:
    var current := source_root if relative_dir.is_empty() else source_root.path_join(relative_dir)
    var added := 0
    var files := DirAccess.get_files_at(current)
    files.sort()
    for filename in files:
        if filename.to_lower().ends_with(".pck"):
            continue
        var relative_file := filename if relative_dir.is_empty() else relative_dir.path_join(filename)
        var target_path := TARGET_ROOT + relative_file
        var source_path := current.path_join(filename)
        var err := packer.add_file(target_path, source_path)
        if err != OK:
            push_error("Could not add map resource " + source_path + ": " + str(err))
            return -1
        added += 1
    var directories := DirAccess.get_directories_at(current)
    directories.sort()
    for directory_name in directories:
        if directory_name.begins_with("."):
            continue
        var child_relative := directory_name if relative_dir.is_empty() else relative_dir.path_join(directory_name)
        var child_added := _add_directory(packer, source_root, child_relative)
        if child_added < 0:
            return -1
        added += child_added
    return added
