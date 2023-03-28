# Computer-Graphic
Course Labs and Projects

## Self-Learning
[Tutorial](https://learnopengl-cn.github.io/01%20Getting%20started/03%20Hello%20Window/)

## Some Basic Components
[Reference-Important](https://learnopengl-cn.github.io/01%20Getting%20started/04%20Hello%20Triangle/)
1. Graphics Pipeline
	1. **Vertex Shader**
	2. Primitice Assembly -> Let points to become a primitice (Using **Element Buffer Object**)
	3. Geometry Shader
	4. Rasterization Stage
	5. **Fragment Shader** -> Calculate the final color (**illumination, Shade, color of light...**)
	6. Blending -> Alpha...

2. Main Process
	1. 复制顶点数组到缓冲中供OpenGL使用
	2. 设置顶点属性指针
	3. 当我们渲染一个物体时要使用着色器程序
	4. 绘制物体

Ps. Shader Program Object: Link shaders (the output should match the next input)
	
