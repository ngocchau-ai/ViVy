# Origin Session Summary

Người sáng lập muốn xây một model mới có bản sắc riêng, không chỉ là bản chưng cất của model có sẵn. Model được hình dung như một nhà khoa học xuất sắc: không học và tự làm mọi thứ từ đầu, mà duy trì nhiều hướng tư duy, lập kế hoạch, giao nhiệm vụ cho các executor và xác minh bằng chứng.

Ba tài liệu nguồn phản ánh ba giai đoạn tư duy:

1. Gemini: polyhedral constraints, cutting plane, soft-qubit, DataContract và orchestrator.
2. DeepSeek: unitary reasoner, Hilbert/tensor state-space, projection và delegation.
3. Grok: hybrid synthesis, self-verification và multi-teacher distillation.

Kiến trúc cuối được tái cấu trúc thành NPS Core:

- `N_h` hypothesis, `N_v` verification needs, `N_e` executors.
- Adaptive N.
- Thought ecology.
- Experiment Designer.
- Evidence Packet.
- Verification Tribunal.
- Runtime identity độc lập với backbone model.

Trong phát triển phần mềm, Codex chỉ điều phối; mọi code do model local thực hiện. Codegraph là bản đồ sống và phải luôn đồng bộ với repository HEAD. Memory được phân tầng để giảm token và tránh project lag.
