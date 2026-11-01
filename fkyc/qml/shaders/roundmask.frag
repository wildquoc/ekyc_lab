#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 size;
    float radius;
};

layout(binding = 1) uniform sampler2D source;

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 p = (uv - vec2(0.5)) * size;
    vec2 halfSize = size * 0.5 - vec2(1.5);
    float r = min(radius, min(halfSize.x, halfSize.y) - 0.5);
    float d = sdRoundBox(p, halfSize, r);
    float af = max(1.4, fwidth(d) * 1.25);
    float mask = 1.0 - smoothstep(-af, af, d);
    if (mask <= 0.001) {
        fragColor = vec4(0.0);
        return;
    }
    vec4 col = texture(source, uv);
    fragColor = vec4(col.rgb, col.a * mask) * qt_Opacity;
}
