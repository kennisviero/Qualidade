import { Injectable } from '@angular/core';
import { NGXLogger } from 'ngx-logger';
import { SpreadSheetService } from '../../spreadsheet.service';
import { ClipboardService } from '../../clipboard.service';
import { ExportStrategy, ExportOptions, ExportResult } from './export.strategy';
import { IList } from 'src/app/model/interfaces/IList';
import { REQUIREMENT_TYPE, REQUIREMENT_DISPLAY_NAME_MAP } from 'src/app/constants/app.constants';
import { EXPORT_FILE_FORMATS, SPREADSHEET_HEADER_ROW } from 'src/app/constants/export.constants';

type TestCaseStep = {
  number: number;
  action: string;
  expectedResult: string;
};

type FormattedTestCase = {
  id: string;
  us_id: string;
  prd_id: string;
  title: string;
  description: string;
  preConditions: string;
  postConditions: string;
  priority: string;
  type: string;
  steps: TestCaseStep[];
};

@Injectable({
  providedIn: 'root',
})
export class TestCaseExportStrategy implements ExportStrategy {
  constructor(
    private exportService: SpreadSheetService,
    private logger: NGXLogger,
    private clipboardService: ClipboardService,
  ) {}

  async export(data: IList[], options: ExportOptions): Promise<ExportResult> {
    try {
      const { format: exportFormat, projectName } = options;
      const testCases = this.transformData(data);

      let success = true;

      switch (exportFormat) {
        case EXPORT_FILE_FORMATS.JSON: {
          success = this.clipboardService.copyToClipboard(JSON.stringify(testCases, null, 2));
          break;
        }
        case EXPORT_FILE_FORMATS.EXCEL: {
          const transformedData = this.transformToRows(testCases);
          const fileName = `${projectName}_${REQUIREMENT_TYPE.TC.toLowerCase()}`;
          this.exportToExcel(transformedData, fileName);
          break;
        }
        default: {
          throw new Error(`Format ${exportFormat} not supported`);
        }
      }

      return { success };
    } catch (error) {
      this.logger.error('Test case export failed:', error);
      return { success: false, error: error as Error };
    }
  }

  private transformData(data: IList[]): FormattedTestCase[] {
    return data.map(item => {
      const content = typeof item.content === 'string' ? JSON.parse(item.content) : item.content;
      const fileName = item.fileName;
      
      // Extract userStoryId from filename if possible (assuming format like US1/TC01-base.json)
      const userStoryIdMatch = fileName.match(/([^/]+)\/[^/]+\.json$/);
      const extractedUserStoryId = userStoryIdMatch ? userStoryIdMatch[1] : '';

      return {
        id: content.id || '',
        us_id: content.us_id || extractedUserStoryId || '',
        prd_id: content.prd_id || '',
        title: content.title || '',
        description: content.description || '',
        preConditions: content.preConditions || '',
        postConditions: content.postConditions || '',
        priority: content.priority || '',
        type: content.type || '',
        steps: Array.isArray(content.steps) 
          ? content.steps.map((step: any, index: number) => ({
              number: index + 1,
              action: step.action || '',
              expectedResult: step.expectedResult || ''
            }))
          : []
      };
    });
  }

  private transformToRows(testCases: FormattedTestCase[]): Array<string[]> {
    return testCases.map(tc => [
      tc.id,
      tc.us_id,
      tc.prd_id,
      tc.title,
      tc.description,
      tc.preConditions,
      tc.postConditions,
      tc.priority,
      tc.type,
      tc.steps.map(step => 
        `${step.number}. ${step.action} => ${step.expectedResult}`
      ).join('\n')
    ]);
  }

  private exportToExcel(rows: Array<string[]>, fileName: string): void {
    this.exportService.exportToExcel(
      [{
        name: REQUIREMENT_DISPLAY_NAME_MAP[REQUIREMENT_TYPE.TC],
        data: [SPREADSHEET_HEADER_ROW[REQUIREMENT_TYPE.TC], ...rows]
      }],
      fileName
    );
  }
}
