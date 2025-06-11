export interface ICommentItem {
  id: string;
  imgSrc: string;
  ico: string;
  name: string;
  subject: string;
  commentText: string;
  value: string;
  datetime: string;
}

export interface IDropdown {
  caption?: string;
  icon?: string;
  enableIcon?: boolean;
  disabled?: boolean;
  closeOnSelect?: boolean;
  list: Array<{
    id: string | number;
    isActive: boolean;
    label: string;
  }>;
  setList: React.Dispatch<React.SetStateAction<IDropdown["list"]>>
  onSelect?: (e: React.MouseEvent<HTMLLIElement>, id?: string | number) => void
}