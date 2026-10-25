export class SetFlowChartAction {
  static readonly type = '[Business Process] Set flow chart';
  constructor(
    public relativePath: string,
    public content: string,
  ) {}
}

export class GetFlowChartAction {
  static readonly type = '[Business Process] Get flow chart';
  constructor(public relativePath: string) {}
}
