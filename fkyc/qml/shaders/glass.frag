#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 size;
    vec2 texSize;
    float radius;
    float pad;
    float strength;
};

layout(binding = 1) uniform sampler2D source;

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 p = (uv - vec2(0.5)) * size;
    vec2 halfSize = size * 0.5 - vec2(2.25);
    float r = min(radius, min(halfSize.x, halfSize.y) - 0.5);
    float d = sdRoundBox(p, halfSize, r);

    float af = max(1.8, fwidth(d) * 1.35);
    float mask = 1.0 - smoothstep(-af, af, d);
    if (mask <= 0.001) {
        fragColor = vec4(0.0);
        return;
    }

    float e = 2.4;
    vec2 n = vec2(
        sdRoundBox(p + vec2(e, 0.0), halfSize, r) - sdRoundBox(p - vec2(e, 0.0), halfSize, r),
        sdRoundBox(p + vec2(0.0, e), halfSize, r) - sdRoundBox(p - vec2(0.0, e), halfSize, r)
    );
    n = normalize(n + vec2(1e-5));

    float rim = smoothstep(-22.0, -8.0, d) * (1.0 - smoothstep(-3.0, af, d));
    float inner = smoothstep(-12.0, -2.0, d);
    vec2 offsetPx = n * rim * strength;
    vec2 base = vec2(pad, pad) / texSize + uv * (size / texSize);
    vec2 ruv = clamp(base + offsetPx / texSize, vec2(0.001), vec2(0.999));

    vec3 col = texture(source, ruv).rgb;

    float frost = 0.10 + rim * 0.02;
    col = mix(col, vec3(1.0), frost);

    float depthShade = 1.0 - inner * 0.08;
    float centerLift = (1.0 - rim) * 0.02;
    col *= depthShade;
    col += vec3(1.0) * centerLift;

    float spec = pow(clamp(dot(n, normalize(vec2(-0.45, -0.75))) * 0.5 + 0.5, 0.0, 1.0), 20.0);
    col += vec3(1.0) * spec * rim * 0.05;

    fragColor = vec4(col, mask) * qt_Opacity;
}
