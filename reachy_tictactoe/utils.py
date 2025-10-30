piece2id = {
    'none': 0,
    'cube': 1,
    'cylinder': 2,
}

id2piece = {
    v: k for k, v in piece2id.items()
}

piece2player = {
    'cube': 'human',
    'cylinder': 'robot',
    'none': 'nobody',
}
