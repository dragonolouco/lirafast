from obj_render import make_cube, make_heightmap, read_obj, write_obj


def test_cube_has_closed_triangle_mesh(tmp_path):
    mesh = make_cube(2)
    path = tmp_path / "cube.obj"
    write_obj(mesh, path)
    loaded = read_obj(path)
    assert len(loaded.vertices) == 8
    assert len(loaded.faces) == 12
    assert loaded.bounds == ((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0))


def test_heightmap_is_reconstructed_from_parameters(tmp_path):
    mesh = make_heightmap(rows=4, cols=5)
    path = tmp_path / "map.obj"
    write_obj(mesh, path)
    loaded = read_obj(path)
    assert len(loaded.vertices) == 20
    assert len(loaded.faces) == 24
    assert loaded.bounds[0][2] < loaded.bounds[1][2]


def test_obj_reader_triangulates_polygon_faces(tmp_path):
    path = tmp_path / "quad.obj"
    path.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n", encoding="utf-8")
    mesh = read_obj(path)
    assert mesh.faces == [(0, 1, 2), (0, 2, 3)]
