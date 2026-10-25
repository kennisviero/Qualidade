import { Injectable } from '@angular/core';
import { Action, Selector, State, StateContext } from '@ngxs/store';
import {
  SetFlowChartAction,
  GetFlowChartAction,
} from './business-process.actions';
import { AppSystemService } from '../../services/app-system/app-system.service';

export class BusinessProcessStateModel {
  selectedFlowChart!: string;
}

@State<BusinessProcessStateModel>({
  name: 'businessProcess',
  defaults: {
    selectedFlowChart: '',
  },
})
@Injectable()
export class BusinessProcessState {
  constructor(private appSystemService: AppSystemService) {}

  @Selector()
  static getSelectedFlowChart(state: BusinessProcessStateModel) {
    return state.selectedFlowChart;
  }

  @Action(GetFlowChartAction)
  async getFlowChart(
    { getState, patchState }: StateContext<BusinessProcessStateModel>,
    { relativePath }: GetFlowChartAction,
  ) {
    const response = await this.appSystemService.readFile(relativePath);
    const parsedContent = JSON.parse(response);
    const state = getState();
    patchState({
      ...state,
      selectedFlowChart: parsedContent.flowChartDiagram,
    });
  }

  @Action(SetFlowChartAction)
  async setFlowChart(
    { getState, patchState }: StateContext<BusinessProcessStateModel>,
    { relativePath, content }: SetFlowChartAction,
  ) {
    const response = await this.appSystemService.readFile(relativePath);
    const parsedContent = JSON.parse(response);
    parsedContent.flowChartDiagram = content;
    await this.appSystemService.createFileWithContent(
      relativePath,
      JSON.stringify(parsedContent),
    );
    const state = getState();
    patchState({
      ...state,
      selectedFlowChart: content,
    });
  }
}
